from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from web3 import Web3

from app.alchemy_client import AlchemyOracle, OracleDataError
from app.config import ALCHEMY_API_KEY
from app.features import (
    WalletFeatures,
    extract_wallet_features,
    validate_ethereum_address,
)
from app.models import CreditScoreResponse, ErrorResponse, ScoreFactor
from app.protocol_behaviour import decode_aave_v3_receipt
from app.protocols import DEFI_PROTOCOLS
from app.scoring import compute_risk_score

oracle = AlchemyOracle(api_key=ALCHEMY_API_KEY)
app = FastAPI(title="DeFi Credit Scoring API", version="0.2.0")


class ScoreRequest(BaseModel):
    address: str = Field(
        ..., description="Ethereum wallet address (0x-prefixed)"
    )


def _validate_address(address: str) -> str:
    if not Web3.is_address(address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address")
    return Web3.to_checksum_address(address)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _get_wallet_analysis(address: str):
    """Core pipeline: Ingest transfers -> Decode Receipts -> Extract Features."""
    checksum = _validate_address(address)

    try:
        raw_transfers = oracle.fetch_asset_transfers(checksum)
    except OracleDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Blockchain provider error: {exc}"
        ) from exc

    # Identify transactions targeting Aave contracts
    aave_addresses = [
        addr.lower()
        for addr in DEFI_PROTOCOLS.get("aave", {}).get("addresses", [])
    ]
    aave_tx_hashes_ordered: list[str] = []

    for t in raw_transfers:
        to_addr = (t.get("to") or "").lower()
        from_addr = (t.get("from") or "").lower()
        if to_addr in aave_addresses or from_addr in aave_addresses:
            tx_hash = t.get("hash")
            if tx_hash and tx_hash not in aave_tx_hashes_ordered:
                aave_tx_hashes_ordered.append(tx_hash)

    defi_actions = []
    # Fetch receipts for the 15 most recent interactions to avoid timeouts
    for tx_hash in aave_tx_hashes_ordered[-15:]:
        try:
            receipt = oracle.fetch_transaction_receipt(tx_hash)
            if receipt:
                actions = decode_aave_v3_receipt(
                    receipt,
                    DEFI_PROTOCOLS.get("aave", {}).get("addresses", []),
                )
                defi_actions.extend(actions)
        except Exception:
            # Gracefully ignore receipt failures to avoid aborting the overall analysis
            continue

    features = extract_wallet_features(
        checksum, raw_transfers, defi_actions=defi_actions
    )
    return checksum, features


@app.get("/wallet/{wallet_address}/features", response_model=WalletFeatures)
def get_wallet_features(wallet_address: str):
    _, features = _get_wallet_analysis(wallet_address)
    return features


def score_wallet(address: str) -> CreditScoreResponse:
    checksum, features = _get_wallet_analysis(address)

    if features.unique_transaction_count == 0:
        return CreditScoreResponse(
            address=checksum,
            score=300,
            new_wallet=True,
            features=features,
            explanations=[
                ScoreFactor(
                    factor="No History",
                    impact="neutral",
                    description="Wallet has no on-chain history.",
                )
            ],
        )

    score, explanations = compute_risk_score(features)

    return CreditScoreResponse(
        address=checksum,
        score=score,
        new_wallet=False,
        features=features,
        explanations=[ScoreFactor(**e) for e in explanations],
    )


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
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail}
    )