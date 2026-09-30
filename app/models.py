from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class ScoreBreakdown(BaseModel):
    account_age: float = Field(ge=0, le=1)
    transaction_count: float = Field(ge=0, le=1)
    defi_interactions: float = Field(ge=0, le=1)

class WalletMetricsResponse(BaseModel):
    account_age_days: float
    transaction_count: int
    defi_interaction_count: int
    protocols_used: list[str]

class CreditScoreResponse(BaseModel):
    address: str
    score: int = Field(ge=300, le=850)
    new_wallet: bool
    metrics: WalletMetricsResponse
    normalized: ScoreBreakdown
    message: str | None = None

class ErrorResponse(BaseModel):
    detail: str

# --- Phase 2B: Structured Action Evidence ---
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

    # Phase 2A: Protocol Interaction Features
    protocols_used: List[str] = Field(default_factory=list)
    protocol_count: int = Field(default=0, ge=0)
    lending_protocol_count: int = Field(default=0, ge=0)
    dex_protocol_count: int = Field(default=0, ge=0)
    defi_transaction_count: int = Field(default=0, ge=0)
    defi_active_days: int = Field(default=0, ge=0)

    # --- Phase 2B: Action Detection Features ---
    borrow_count: int = Field(default=0, ge=0)
    deposit_count: int = Field(default=0, ge=0)
    repayment_count: int = Field(default=0, ge=0)
    withdrawal_count: int = Field(default=0, ge=0)
    liquidation_count: int = Field(default=0, ge=0)
    unknown_action_count: int = Field(default=0, ge=0)

    # Native ETH transfer features
    total_native_eth_transfer_volume: float = Field(default=0.0, ge=0.0)
    average_native_eth_transfer_value: float = Field(default=0.0, ge=0.0)
    median_native_eth_transfer_value: float = Field(default=0.0, ge=0.0)
    analysis_timestamp: str