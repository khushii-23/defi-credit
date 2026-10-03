from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class DeFiAction(BaseModel):
    protocol: str
    action: str
    transaction_hash: str
    participants: List[str]
    evidence: str

class WalletFeatures(BaseModel):
    wallet_address: str
    unique_transaction_count: int = Field(default=0, ge=0)
    asset_transfer_event_count: int = Field(default=0, ge=0)
    first_transaction_timestamp: Optional[str] = None
    last_transaction_timestamp: Optional[str] = None
    wallet_age_days: float = Field(default=0.0, ge=0.0)
    activity_span_days: float = Field(default=0.0, ge=0.0)
    active_days: int = Field(default=0, ge=0)
    transactions_per_active_day: float = Field(default=0.0, ge=0.0)

    protocols_used: List[str] = Field(default_factory=list)
    protocol_count: int = Field(default=0, ge=0)
    lending_protocol_count: int = Field(default=0, ge=0)
    dex_protocol_count: int = Field(default=0, ge=0)
    defi_transaction_count: int = Field(default=0, ge=0)
    defi_active_days: int = Field(default=0, ge=0)

    borrow_count: int = Field(default=0, ge=0)
    deposit_count: int = Field(default=0, ge=0)
    repayment_count: int = Field(default=0, ge=0)
    withdrawal_count: int = Field(default=0, ge=0)
    liquidation_count: int = Field(default=0, ge=0)
    unknown_action_count: int = Field(default=0, ge=0)

    total_native_eth_transfer_volume: float = Field(default=0.0, ge=0.0)
    average_native_eth_transfer_value: float = Field(default=0.0, ge=0.0)
    median_native_eth_transfer_value: float = Field(default=0.0, ge=0.0)
    analysis_timestamp: str

# --- Tasks 3 & 4: Risk Scoring and Explainability ---
class ScoreFactor(BaseModel):
    factor: str
    impact: str  # positive, negative, neutral
    description: str

class CreditScoreResponse(BaseModel):
    address: str
    score: int = Field(ge=300, le=850)
    new_wallet: bool
    features: WalletFeatures
    explanations: List[ScoreFactor]

class ErrorResponse(BaseModel):
    detail: str