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
