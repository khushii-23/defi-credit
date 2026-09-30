from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from web3 import Web3
from fastapi import FastAPI, HTTPException, Path
from app.alchemy_client import get_asset_transfers
from app.features import extract_wallet_features, validate_ethereum_address, WalletFeatures

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


app = FastAPI(title="DeFi Credit Scoring API", version="0.1.0")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/wallet/{wallet_address}/features", response_model=WalletFeatures)
async def get_wallet_features(
    wallet_address: str = Path(..., description="Ethereum wallet hex address")
):
    try:
        norm_address = validate_ethereum_address(wallet_address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        raw_transfers = await get_asset_transfers(norm_address)
    except Exception as err:
        raise HTTPException(status_code=502, detail=f"Blockchain provider error: {str(err)}")

    features = extract_wallet_features(norm_address, raw_transfers)
    return features

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
