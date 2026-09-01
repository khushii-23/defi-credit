from app.config import SCORE_MAX, SCORE_MIN
from app.scoring import (
    WalletMetrics,
    compute_score,
    normalize_account_age,
    normalize_defi_count,
    normalize_tx_count,
)


def test_new_wallet_scores_minimum():
    metrics = WalletMetrics(
        account_age_days=0, transaction_count=0, defi_interaction_count=0
    )
    assert compute_score(metrics) == SCORE_MIN


def test_saturated_metrics_hit_max_score():
    metrics = WalletMetrics(
        account_age_days=10_000,
        transaction_count=10_000,
        defi_interaction_count=10_000,
    )
    assert compute_score(metrics) == SCORE_MAX


def test_score_is_monotonic_in_each_feature():
    base = WalletMetrics(
        account_age_days=30, transaction_count=10, defi_interaction_count=2
    )
    older = WalletMetrics(
        account_age_days=365, transaction_count=10, defi_interaction_count=2
    )
    busier = WalletMetrics(
        account_age_days=30, transaction_count=200, defi_interaction_count=2
    )
    more_defi = WalletMetrics(
        account_age_days=30, transaction_count=10, defi_interaction_count=40
    )
    floor = compute_score(base)
    assert compute_score(older) > floor
    assert compute_score(busier) > floor
    assert compute_score(more_defi) > floor
    assert SCORE_MIN < floor < SCORE_MAX


def test_normalizers_are_bounded():
    assert normalize_account_age(-1) == 0
    assert normalize_account_age(0) == 0
    assert normalize_account_age(10_000) == 1
    assert 0 < normalize_tx_count(1) < 1
    assert normalize_tx_count(0) == 0
    assert normalize_defi_count(0) == 0
    assert normalize_defi_count(10_000) == 1
