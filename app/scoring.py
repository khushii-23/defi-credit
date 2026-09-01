from __future__ import annotations

from dataclasses import dataclass
from math import log1p

from app.config import (
    AGE_DAYS_CAP,
    DEFI_COUNT_CAP,
    SCORE_MAX,
    SCORE_MIN,
    TX_COUNT_CAP,
    WEIGHT_ACCOUNT_AGE,
    WEIGHT_DEFI,
    WEIGHT_TX_COUNT,
)


@dataclass(frozen=True)
class WalletMetrics:
    account_age_days: float
    transaction_count: int
    defi_interaction_count: int
    protocols_used: tuple[str, ...] = ()


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def normalize_account_age(days: float) -> float:
    return _clamp01(days / AGE_DAYS_CAP)


def normalize_tx_count(count: int) -> float:
    # Log scale so a handful of txs still score, while whales saturate at the cap.
    return _clamp01(log1p(count) / log1p(TX_COUNT_CAP))


def normalize_defi_count(count: int) -> float:
    return _clamp01(log1p(count) / log1p(DEFI_COUNT_CAP))


def compute_score(metrics: WalletMetrics) -> int:
    """Map normalized, weighted metrics onto the closed interval [300, 850]."""
    if (
        metrics.account_age_days <= 0
        and metrics.transaction_count <= 0
        and metrics.defi_interaction_count <= 0
    ):
        return SCORE_MIN

    blended = (
        WEIGHT_ACCOUNT_AGE * normalize_account_age(metrics.account_age_days)
        + WEIGHT_TX_COUNT * normalize_tx_count(metrics.transaction_count)
        + WEIGHT_DEFI * normalize_defi_count(metrics.defi_interaction_count)
    )
    raw = SCORE_MIN + (SCORE_MAX - SCORE_MIN) * blended
    return int(round(max(SCORE_MIN, min(SCORE_MAX, raw))))
