"""Decoding validation (paper Section 4.2)."""
from __future__ import annotations
import csv
from collections import Counter
from .decoder import Event

def load_independent(path: str) -> set[tuple]:
    with open(path, newline="") as f:
        return {(r["tx_hash"].lower(), int(r["log_index"]), r["event"], r["account"].lower())
                for r in csv.DictReader(f)}

def compare(ours: list[Event], indep: set[tuple]) -> dict:
    mine = {(e.tx_hash, e.log_index, e.kind, e.account) for e in ours}
    tp = mine & indep
    precision = len(tp) / len(mine) if mine else float("nan")
    recall = len(tp) / len(indep) if indep else float("nan")

    # Separate "event missing" from "event found but attributed to a different account"
    key = lambda s: {(a, b, c) for a, b, c, _ in s}
    wrong_account = (key(mine) & key(indep)) - {(a, b, c) for a, b, c, _ in tp}

    # Per-wallet exact count agreement
    cm = Counter((k, a) for _, _, k, a in mine)
    ci = Counter((k, a) for _, _, k, a in indep)
    keys = set(cm) | set(ci)
    exact = sum(cm[k] == ci[k] for k in keys) / len(keys) if keys else float("nan")

    return {
        "ours": len(mine), "independent": len(indep), "matched": len(tp),
        "precision": precision, "recall": recall, "exact_count_agreement": exact,
        "only_ours": sorted(mine - indep)[:50],          
        "only_independent": sorted(indep - mine)[:50],
        "attribution_mismatches": len(wrong_account),
    }