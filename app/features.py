from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import re
import statistics

from pydantic import BaseModel, Field


ETHEREUM_ADDRESS_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")


def validate_ethereum_address(address: str) -> str:
    """Validate and normalize an Ethereum wallet address."""
    if not address or not ETHEREUM_ADDRESS_REGEX.fullmatch(address):
        raise ValueError(f"Invalid Ethereum address format: {address}")

    return address.lower()


class WalletFeatures(BaseModel):
    wallet_address: str

    # Transaction / activity features
    unique_transaction_count: int = Field(default=0, ge=0)
    asset_transfer_event_count: int = Field(default=0, ge=0)

    first_transaction_timestamp: Optional[str] = None
    last_transaction_timestamp: Optional[str] = None

    wallet_age_days: float = Field(default=0.0, ge=0.0)
    activity_span_days: float = Field(default=0.0, ge=0.0)
    active_days: int = Field(default=0, ge=0)
    transactions_per_active_day: float = Field(default=0.0, ge=0.0)

    # Native ETH transfer features
    total_native_eth_transfer_volume: float = Field(default=0.0, ge=0.0)
    average_native_eth_transfer_value: float = Field(default=0.0, ge=0.0)
    median_native_eth_transfer_value: float = Field(default=0.0, ge=0.0)

    # Reproducibility
    analysis_timestamp: str


def extract_wallet_features(
    wallet_address: str,
    raw_transfers: List[Dict[str, Any]],
    analysis_timestamp: Optional[datetime] = None,
) -> WalletFeatures:
    """
    Convert raw Alchemy asset-transfer records into wallet-level features.

    Important:
    - transfer events are not treated as blockchain transactions
    - unique transaction hashes are used for transaction count
    - failed transaction status is not inferred from transfer data
    - ETH volume refers only to native ETH transfers
    - analysis_timestamp makes wallet-age calculations reproducible
    """

    normalized_address = validate_ethereum_address(wallet_address)

    if analysis_timestamp is None:
        analysis_timestamp = datetime.now(timezone.utc)

    if analysis_timestamp.tzinfo is None:
        analysis_timestamp = analysis_timestamp.replace(tzinfo=timezone.utc)

    analysis_timestamp = analysis_timestamp.astimezone(timezone.utc)

    analysis_timestamp_iso = analysis_timestamp.isoformat()

    if not raw_transfers:
        return WalletFeatures(
            wallet_address=normalized_address,
            analysis_timestamp=analysis_timestamp_iso,
        )

    valid_timestamps: List[datetime] = []
    native_eth_values: List[float] = []
    distinct_dates = set()

    transaction_hashes = set()

    for transfer in raw_transfers:

        # ---------------------------------------------------------
        # Unique transaction hashes
        # ---------------------------------------------------------
        tx_hash = transfer.get("hash")

        if tx_hash:
            transaction_hashes.add(str(tx_hash).lower())

        # ---------------------------------------------------------
        # Timestamp
        # ---------------------------------------------------------
        metadata = transfer.get("metadata", {})

        timestamp = None

        if isinstance(metadata, dict):
            timestamp = metadata.get("blockTimestamp")

        if timestamp:
            try:
                dt = datetime.fromisoformat(
                    str(timestamp).replace("Z", "+00:00")
                )

                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)

                dt = dt.astimezone(timezone.utc)

                valid_timestamps.append(dt)
                distinct_dates.add(dt.date())

            except (ValueError, TypeError):
                pass

        # ---------------------------------------------------------
        # Native ETH transfer volume
        # ---------------------------------------------------------
        asset = transfer.get("asset")
        value = transfer.get("value")

        if asset == "ETH" and value is not None:
            try:
                eth_value = float(value)

                if eth_value >= 0:
                    native_eth_values.append(eth_value)

            except (ValueError, TypeError):
                pass

    transfer_event_count = len(raw_transfers)
    unique_transaction_count = len(transaction_hashes)

    # -------------------------------------------------------------
    # Timestamp calculations
    # -------------------------------------------------------------
    if valid_timestamps:

        sorted_timestamps = sorted(valid_timestamps)

        first_timestamp = sorted_timestamps[0]
        last_timestamp = sorted_timestamps[-1]

        first_timestamp_iso = first_timestamp.isoformat()
        last_timestamp_iso = last_timestamp.isoformat()

        wallet_age_days = max(
            0.0,
            (
                analysis_timestamp - first_timestamp
            ).total_seconds() / 86400.0,
        )

        activity_span_days = max(
            0.0,
            (
                last_timestamp - first_timestamp
            ).total_seconds() / 86400.0,
        )

    else:

        first_timestamp_iso = None
        last_timestamp_iso = None
        wallet_age_days = 0.0
        activity_span_days = 0.0

    # -------------------------------------------------------------
    # Activity calculations
    # -------------------------------------------------------------
    active_days = len(distinct_dates)

    transactions_per_active_day = (
        unique_transaction_count / active_days
        if active_days > 0
        else 0.0
    )

    # -------------------------------------------------------------
    # Native ETH calculations
    # -------------------------------------------------------------
    total_eth_volume = (
        sum(native_eth_values)
        if native_eth_values
        else 0.0
    )

    average_eth_value = (
        total_eth_volume / len(native_eth_values)
        if native_eth_values
        else 0.0
    )

    median_eth_value = (
        statistics.median(native_eth_values)
        if native_eth_values
        else 0.0
    )

    return WalletFeatures(
        wallet_address=normalized_address,

        unique_transaction_count=unique_transaction_count,
        asset_transfer_event_count=transfer_event_count,

        first_transaction_timestamp=first_timestamp_iso,
        last_transaction_timestamp=last_timestamp_iso,

        wallet_age_days=round(wallet_age_days, 2),
        activity_span_days=round(activity_span_days, 2),
        active_days=active_days,

        transactions_per_active_day=round(
            transactions_per_active_day,
            2,
        ),

        total_native_eth_transfer_volume=round(
            total_eth_volume,
            6,
        ),

        average_native_eth_transfer_value=round(
            average_eth_value,
            6,
        ),

        median_native_eth_transfer_value=round(
            median_eth_value,
            6,
        ),

        analysis_timestamp=analysis_timestamp_iso,
    )