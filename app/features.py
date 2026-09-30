# app/features.py
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import statistics
from pydantic import BaseModel, Field, validator
import re

ETHEREUM_ADDRESS_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")

def validate_ethereum_address(address: str) -> str:
    """Validates and returns normalized lowercase Ethereum wallet address."""
    if not address or not ETHEREUM_ADDRESS_REGEX.match(address):
        raise ValueError(f"Invalid Ethereum address format: {address}")
    return address.lower()

class WalletFeatures(BaseModel):
    wallet_address: str
    transaction_count: int = Field(default=0, ge=0)
    first_transaction_timestamp: Optional[str] = None
    last_transaction_timestamp: Optional[str] = None
    wallet_age_days: float = Field(default=0.0, ge=0.0)
    activity_span_days: float = Field(default=0.0, ge=0.0)
    active_days: int = Field(default=0, ge=0)
    transactions_per_active_day: float = Field(default=0.0, ge=0.0)
    total_transaction_volume_eth: float = Field(default=0.0, ge=0.0)
    average_transaction_value_eth: float = Field(default=0.0, ge=0.0)
    median_transaction_value_eth: float = Field(default=0.0, ge=0.0)
    successful_transaction_count: int = Field(default=0, ge=0)
    failed_transaction_count: int = Field(default=0, ge=0)
    failed_transaction_ratio: float = Field(default=0.0, ge=0.0)

def extract_wallet_features(wallet_address: str, raw_transfers: List[Dict[str, Any]]) -> WalletFeatures:
    """
    Transforms raw Alchemy asset transfer records into structured, defensible features.
    Handles zero-transaction edge cases, invalid timestamps, and division-by-zero safeguards.
    """
    norm_address = validate_ethereum_address(wallet_address)
    
    if not raw_transfers:
        return WalletFeatures(wallet_address=norm_address)

    valid_timestamps: List[datetime] = []
    eth_volumes: List[float] = []
    distinct_dates = set()
    successful_count = 0
    failed_count = 0

    for tx in raw_transfers:
        # Check success status if available, default to successful for asset transfers
        category = tx.get("category", "")
        status = tx.get("status", "0x1")
        if status == "0x0" or tx.get("isError") == "1":
            failed_count += 1
        else:
            successful_count += 1

        # Parse timestamp
        meta = tx.get("metadata", {})
        ts_str = meta.get("blockTimestamp") if isinstance(meta, dict) else None
        if ts_str:
            try:
                # Handle ISO timestamps ending with Z or offset
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                valid_timestamps.append(dt)
                distinct_dates.add(dt.date())
            except ValueError:
                pass

        # Parse ETH asset volumes
        asset = tx.get("asset")
        value = tx.get("value")
        if asset == "ETH" and value is not None:
            try:
                eth_val = float(value)
                if eth_val >= 0:
                    eth_volumes.append(eth_val)
            except (ValueError, TypeError):
                pass

    total_tx = len(raw_transfers)
    
    # Temporal Calculations
    now_utc = datetime.now(timezone.utc)
    if valid_timestamps:
        sorted_ts = sorted(valid_timestamps)
        first_ts = sorted_ts[0]
        last_ts = sorted_ts[-1]
        
        first_iso = first_ts.isoformat()
        last_iso = last_ts.isoformat()
        
        wallet_age = max(0.0, (now_utc - first_ts).total_seconds() / 86400.0)
        activity_span = max(0.0, (last_ts - first_ts).total_seconds() / 86400.0)
    else:
        first_iso = None
        last_iso = None
        wallet_age = 0.0
        activity_span = 0.0

    active_days_cnt = len(distinct_dates)
    tx_per_active_day = (total_tx / active_days_cnt) if active_days_cnt > 0 else 0.0

    # Volume Calculations
    tot_vol = sum(eth_volumes) if eth_volumes else 0.0
    avg_vol = (tot_vol / len(eth_volumes)) if eth_volumes else 0.0
    med_vol = statistics.median(eth_volumes) if eth_volumes else 0.0

    # Fail Ratio Calculation
    fail_ratio = (failed_count / total_tx) if total_tx > 0 else 0.0

    return WalletFeatures(
        wallet_address=norm_address,
        transaction_count=total_tx,
        first_transaction_timestamp=first_iso,
        last_transaction_timestamp=last_iso,
        wallet_age_days=round(wallet_age, 2),
        activity_span_days=round(activity_span, 2),
        active_days=active_days_cnt,
        transactions_per_active_day=round(tx_per_active_day, 2),
        total_transaction_volume_eth=round(tot_vol, 6),
        average_transaction_value_eth=round(avg_vol, 6),
        median_transaction_value_eth=round(med_vol, 6),
        successful_transaction_count=successful_count,
        failed_transaction_count=failed_count,
        failed_transaction_ratio=round(fail_ratio, 4)
    )