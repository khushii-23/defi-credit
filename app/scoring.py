from __future__ import annotations

from app.config import SCORE_MAX, SCORE_MIN
from app.models import WalletFeatures


def _clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))


def compute_risk_score(features: WalletFeatures) -> tuple[int, list[dict]]:
    """Task 3 & 4: Risk-Adjusted Scoring Engine & Explainability Layer.

    Computes a risk-adjusted score using Phase 2 metrics and generates
    explainable factors. Returns: (score, explanations)
    """
    if features.unique_transaction_count == 0:
        return SCORE_MIN, [
            {
                "factor": "No History",
                "impact": "neutral",
                "description": "Wallet has no on-chain transactions.",
            }
        ]

    base_score = 300
    points = 0.0
    explanations: list[dict] = []

    # 1. Account Age (Up to 150 points) - ONLY awarded if wallet actively uses DeFi
    age_points = _clamp((features.wallet_age_days / 365.0) * 150.0, 0.0, 150.0)
    if features.defi_transaction_count > 0:
        points += age_points
        if age_points > 50.0:
            explanations.append(
                {
                    "factor": "Account Age",
                    "impact": "positive",
                    "description": f"Wallet active for {int(features.wallet_age_days)} days.",
                }
            )
        else:
            explanations.append(
                {
                    "factor": "Account Age",
                    "impact": "negative",
                    "description": "Relatively new wallet history.",
                }
            )
    else:
        explanations.append(
            {
                "factor": "Account Age",
                "impact": "neutral",
                "description": "Age ignored due to lack of DeFi engagement.",
            }
        )

    # 2. DeFi Activity (Up to 150 points)
    defi_tx = features.defi_transaction_count
    defi_points = _clamp(defi_tx * 3.0, 0.0, 150.0)
    points += defi_points
    if defi_points > 0.0:
        explanations.append(
            {
                "factor": "DeFi Engagement",
                "impact": "positive",
                "description": f"Executed {defi_tx} DeFi transactions.",
            }
        )

    # 3. Lending Behavior (Phase 2B Metrics)
    repay_bonus = _clamp(features.repayment_count * 25.0, 0.0, 150.0)
    deposit_bonus = _clamp(features.deposit_count * 15.0, 0.0, 100.0)

    if repay_bonus > 0.0:
        points += repay_bonus
        explanations.append(
            {
                "factor": "Loan Repayment",
                "impact": "positive",
                "description": f"Detected {features.repayment_count} protocol repayments.",
            }
        )
    if deposit_bonus > 0.0:
        points += deposit_bonus
        explanations.append(
            {
                "factor": "Collateral Supply",
                "impact": "positive",
                "description": f"Detected {features.deposit_count} protocol deposits.",
            }
        )

    # Penalties (Liquidations severely impact score)
    liquidation_penalty = _clamp(features.liquidation_count * 200.0, 0.0, 500.0)
    if liquidation_penalty > 0.0:
        points -= liquidation_penalty
        explanations.append(
            {
                "factor": "Liquidations",
                "impact": "negative",
                "description": f"High risk: Detected {features.liquidation_count} liquidation events.",
            }
        )

    final_score = int(
        round(_clamp(base_score + points, float(SCORE_MIN), float(SCORE_MAX)))
    )

    # HARD CAP: A liquidated wallet cannot have a prime score (> 600)
    if features.liquidation_count > 0 and final_score > 600:
        final_score = 600
        explanations.append(
            {
                "factor": "Risk Cap Applied",
                "impact": "negative",
                "description": "Score capped at 600 due to historical liquidations.",
            }
        )

    return final_score, explanations