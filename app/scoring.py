"""Deterministic additive score on [300, 850] with reason codes (paper Section 3.3-3.6)."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

DAY = 86400

@dataclass(frozen=True)
class ScoreEvent:
    kind: str                       # Supply | Borrow | Repay | LiquidationCall
    ts: int                         # unix seconds
    asset: str
    usd: float                      # USD value at event block (price source: your choice)
    debt_usd: Optional[float] = None  # outstanding debt before a Repay, if known

@dataclass(frozen=True)
class Config:
    base: int = 300
    floor: int = 300
    ceil: int = 850
    min_usd: float = 50.0
    repay_debt_frac: float = 0.05
    repay_rule: str = "or"          
    repay_pts: int = 25
    repay_cap: int = 150
    supply_pts: int = 15
    supply_cap: int = 60
    month_pts: int = 5
    month_cap: int = 60
    age_step: int = 10
    age_cap: int = 60
    liq_penalty: int = 50           # Updated to V2 parameter (was 200)
    liq_cap_score: int = 600
    liq_cap_days: int = 365
    thin_file_gate: bool = True
    daily_limit: bool = True

@dataclass
class ScoreResult:
    final: int
    raw: int
    components: dict
    reasons: list = field(default_factory=list)
    cap_active: bool = False
    cap_binding: bool = False        # True only if the cap actually lowered the score

def _qualifies(e: ScoreEvent, c: Config) -> bool:
    if e.kind == "Supply":
        return e.usd >= c.min_usd
    if e.kind == "Repay":
        by_usd = e.usd >= c.min_usd
        by_frac = e.debt_usd is not None and e.debt_usd > 0 and e.usd >= c.repay_debt_frac * e.debt_usd
        return (by_usd and by_frac) if c.repay_rule == "and" and e.debt_usd is not None else (by_usd or by_frac)
    return False

def _utc_day(ts: int) -> int:
    return ts // DAY

def _ym(ts: int):
    d = datetime.fromtimestamp(ts, tz=timezone.utc)
    return d.year, d.month

def score(events: list[ScoreEvent], t: int, cfg: Config = Config()) -> ScoreResult:
    """Score one wallet at snapshot time t using only events with ts <= t."""
    ev = sorted((e for e in events if e.ts <= t), key=lambda e: e.ts)
    lending = [e for e in ev if e.kind in ("Supply", "Borrow", "Repay")]
    liqs = [e for e in ev if e.kind == "LiquidationCall"]

    def counted(kind):
        seen, n = set(), 0
        for e in ev:
            if e.kind != kind or not _qualifies(e, cfg):
                continue
            key = (e.asset, _utc_day(e.ts))
            if cfg.daily_limit:
                if key in seen:
                    continue
                seen.add(key)
            n += 1
        return n

    n_rep, n_sup = counted("Repay"), counted("Supply")
    p_rep = min(cfg.repay_cap, cfg.repay_pts * n_rep)
    p_sup = min(cfg.supply_cap, cfg.supply_pts * n_sup)

    months = {_ym(e.ts) for e in ev if e.kind in ("Repay", "Supply") and _qualifies(e, cfg)}
    p_brd = min(cfg.month_cap, cfg.month_pts * len(months))

    n_defi = len(lending)
    p_age = 0
    if n_defi > 0 or not cfg.thin_file_gate:
        first = lending[0].ts if lending else (ev[0].ts if ev else t)
        m = int((t - first) / (30.4375 * DAY))
        p_age = min(cfg.age_cap, cfg.age_step * (m // 6))

    L = len(liqs)
    p_liq = -cfg.liq_penalty * L
    raw = cfg.base + p_rep + p_sup + p_brd + p_age + p_liq

    cap_active = any(t - e.ts < cfg.liq_cap_days * DAY for e in liqs)
    capped = min(raw, cfg.liq_cap_score) if cap_active else raw
    final = max(cfg.floor, min(cfg.ceil, capped))

    comps = {"base": cfg.base, "repay": p_rep, "supply": p_sup, "breadth": p_brd,
             "age": p_age, "liquidation": p_liq}
    reasons = []
    if n_rep:
        reasons.append(f"R1: {n_rep} qualifying repayments (+{p_rep}" + (", capped)" if p_rep == cfg.repay_cap else ")"))
    if n_sup:
        reasons.append(f"R2: {n_sup} qualifying supplies (+{p_sup}" + (", capped)" if p_sup == cfg.supply_cap else ")"))
    if months:
        reasons.append(f"R3: {len(months)} active months (+{p_brd})")
    if p_age:
        reasons.append(f"R4: lending history age (+{p_age})")
    if n_defi == 0:
        reasons.append("R5: thin file, no lending activity (age points withheld)")
    if L:
        reasons.append(f"R6: {L} liquidation(s) ({p_liq})")
    if cap_active:
        reasons.append(f"R7: liquidation within {cfg.liq_cap_days}d, cap {cfg.liq_cap_score} active")

    return ScoreResult(final=final, raw=raw, components=comps, reasons=reasons,
                       cap_active=cap_active, cap_binding=cap_active and raw > cfg.liq_cap_score)

def max_raw_with_liquidations(cfg: Config, n_liq: int = 1) -> int:
    """Upper bound of the raw score for a wallet with n_liq liquidations."""
    return cfg.base + cfg.repay_cap + cfg.supply_cap + cfg.month_cap + cfg.age_cap - cfg.liq_penalty * n_liq