from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from web3 import Web3

from app.alchemy_client import AlchemyOracle, NewWalletError, OracleDataError
from app.config import ALCHEMY_API_KEY, SCORE_MIN
from app.models import CreditScoreResponse, ErrorResponse, ScoreBreakdown, WalletMetricsResponse
from app.scoring import (
    WalletMetrics,
    compute_score,
    normalize_account_age,
    normalize_defi_count,
    normalize_tx_count,
)

app = FastAPI(
    title="DeFi Credit Oracle",
    description="Off-chain oracle that scores Ethereum wallets from Alchemy on-chain history.",
    version="1.0.0",
)

oracle = AlchemyOracle(api_key=ALCHEMY_API_KEY)


class ScoreRequest(BaseModel):
    address: str = Field(..., description="Ethereum wallet address (0x-prefixed)")


def _validate_address(address: str) -> str:
    if not Web3.is_address(address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address")
    return Web3.to_checksum_address(address)


def _build_response(
    address: str,
    metrics: WalletMetrics,
    *,
    new_wallet: bool,
    message: str | None = None,
) -> CreditScoreResponse:
    score = SCORE_MIN if new_wallet else compute_score(metrics)
    return CreditScoreResponse(
        address=address,
        score=score,
        new_wallet=new_wallet,
        metrics=WalletMetricsResponse(
            account_age_days=round(metrics.account_age_days, 4),
            transaction_count=metrics.transaction_count,
            defi_interaction_count=metrics.defi_interaction_count,
            protocols_used=list(metrics.protocols_used),
        ),
        normalized=ScoreBreakdown(
            account_age=round(normalize_account_age(metrics.account_age_days), 4),
            transaction_count=round(normalize_tx_count(metrics.transaction_count), 4),
            defi_interactions=round(
                normalize_defi_count(metrics.defi_interaction_count), 4
            ),
        ),
        message=message,
    )


def score_wallet(address: str) -> CreditScoreResponse:
    checksum = _validate_address(address)
    try:
        metrics = oracle.fetch_metrics(checksum)
    except NewWalletError:
        empty = WalletMetrics(
            account_age_days=0,
            transaction_count=0,
            defi_interaction_count=0,
        )
        return _build_response(
            checksum,
            empty,
            new_wallet=True,
            message="Wallet has no on-chain history; returning the minimum score of 300.",
        )
    except OracleDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _build_response(checksum, metrics, new_wallet=False)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/score/{address}",
    response_model=CreditScoreResponse,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def get_score(address: str) -> CreditScoreResponse:
    return score_wallet(address)


@app.post(
    "/score",
    response_model=CreditScoreResponse,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def post_score(body: ScoreRequest) -> CreditScoreResponse:
    return score_wallet(body.address)


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
