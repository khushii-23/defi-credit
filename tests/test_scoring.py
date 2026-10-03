from app.config import SCORE_MAX, SCORE_MIN
from app.scoring import compute_risk_score
from app.models import WalletFeatures

def _mock_features(**kwargs) -> WalletFeatures:
    data = {
        "wallet_address": "0x0000000000000000000000000000000000000001",
        "analysis_timestamp": "2026-01-01T00:00:00+00:00"
    }
    data.update(kwargs)
    return WalletFeatures(**data)

def test_new_wallet_scores_minimum():
    features = _mock_features(unique_transaction_count=0)
    score, _ = compute_risk_score(features)
    assert score == SCORE_MIN

def test_saturated_metrics_hit_max_score():
    features = _mock_features(
        unique_transaction_count=1000,
        wallet_age_days=1000,
        defi_transaction_count=500,
        repayment_count=50,
        deposit_count=50,
        liquidation_count=0
    )
    score, _ = compute_risk_score(features)
    assert score == SCORE_MAX

def test_score_is_monotonic_in_each_feature():
    base = _mock_features(unique_transaction_count=10, wallet_age_days=30, defi_transaction_count=2, repayment_count=0)
    older = _mock_features(unique_transaction_count=10, wallet_age_days=365, defi_transaction_count=2, repayment_count=0)
    more_defi = _mock_features(unique_transaction_count=10, wallet_age_days=30, defi_transaction_count=20, repayment_count=0)
    repayments = _mock_features(unique_transaction_count=10, wallet_age_days=30, defi_transaction_count=2, repayment_count=5)
    
    floor, _ = compute_risk_score(base)
    assert compute_risk_score(older)[0] > floor
    assert compute_risk_score(more_defi)[0] > floor
    assert compute_risk_score(repayments)[0] > floor

def test_liquidations_penalize_score():
    healthy = _mock_features(unique_transaction_count=10, wallet_age_days=365, repayment_count=10, liquidation_count=0)
    liquidated = _mock_features(unique_transaction_count=10, wallet_age_days=365, repayment_count=10, liquidation_count=2)
    
    healthy_score, _ = compute_risk_score(healthy)
    liquidated_score, _ = compute_risk_score(liquidated)
    
    assert liquidated_score < healthy_score