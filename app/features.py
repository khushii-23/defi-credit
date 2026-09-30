from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import re
import statistics

from web3 import Web3
from app.models import WalletFeatures, DeFiAction
from app.protocols import PROTOCOL_BY_ADDRESS

ETHEREUM_ADDRESS_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")

def validate_ethereum_address(address: str) -> str:
    """Validate and normalize an Ethereum wallet address."""
    if not address or not ETHEREUM_ADDRESS_REGEX.fullmatch(address):
        raise ValueError(f"Invalid Ethereum address format: {address}")
    return address.lower()

def extract_wallet_features(
    wallet_address: str,
    raw_transfers: List[Dict[str, Any]],
    analysis_timestamp: Optional[datetime] = None,
    defi_actions: Optional[List[DeFiAction]] = None,
) -> WalletFeatures:
    """
    Convert raw Alchemy asset-transfer records into wallet-level features.
    """
    normalized_address = validate_ethereum_address(wallet_address)

    if analysis_timestamp is None:
        analysis_timestamp = datetime.now(timezone.utc)
    if analysis_timestamp.tzinfo is None:
        analysis_timestamp = analysis_timestamp.replace(tzinfo=timezone.utc)
    analysis_timestamp = analysis_timestamp.astimezone(timezone.utc)
    analysis_timestamp_iso = analysis_timestamp.isoformat()

    # Early return if absolutely no history exists
    if not raw_transfers and not defi_actions:
        return WalletFeatures(
            wallet_address=normalized_address,
            analysis_timestamp=analysis_timestamp_iso,
        )

    valid_timestamps: List[datetime] = []
    native_eth_values: List[float] = []
    distinct_dates = set()
    transaction_hashes = set()

    # Phase 2A tracking sets
    defi_transaction_hashes = set()
    protocols_interacted = set()
    lending_protocols = set()
    dex_protocols = set()
    defi_distinct_dates = set()

    for transfer in raw_transfers:
        # Unique transaction hashes
        tx_hash = transfer.get("hash")
        if tx_hash:
            tx_hash_str = str(tx_hash).lower()
            transaction_hashes.add(tx_hash_str)

        # Timestamp logic
        metadata = transfer.get("metadata", {})
        timestamp = None
        if isinstance(metadata, dict):
            timestamp = metadata.get("blockTimestamp")

        dt = None
        if timestamp:
            try:
                dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dt = dt.astimezone(timezone.utc)
                valid_timestamps.append(dt)
                distinct_dates.add(dt.date())
            except (ValueError, TypeError):
                pass

        # Native ETH logic
        asset = transfer.get("asset")
        value = transfer.get("value")
        if asset == "ETH" and value is not None:
            try:
                eth_value = float(value)
                if eth_value >= 0:
                    native_eth_values.append(eth_value)
            except (ValueError, TypeError):
                pass

        # --- Phase 2A: Protocol Identification Logic ---
        to_address = transfer.get("to")
        from_address = transfer.get("from")
        
        protocol_info = None
        
        # Check if receiver is a known protocol
        if to_address and Web3.is_address(to_address):
            protocol_info = PROTOCOL_BY_ADDRESS.get(Web3.to_checksum_address(to_address))
            
        # Check if sender is a known protocol (if receiver didn't match)
        if not protocol_info and from_address and Web3.is_address(from_address):
            protocol_info = PROTOCOL_BY_ADDRESS.get(Web3.to_checksum_address(from_address))

        if protocol_info:
            protocol_name = protocol_info["name"]
            protocol_category = protocol_info["category"]
            
            protocols_interacted.add(protocol_name)
            
            if protocol_category == "lending":
                lending_protocols.add(protocol_name)
            elif protocol_category == "dex":
                dex_protocols.add(protocol_name)
                
            if tx_hash:
                defi_transaction_hashes.add(tx_hash_str)
            if dt:
                defi_distinct_dates.add(dt.date())

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
            (analysis_timestamp - first_timestamp).total_seconds() / 86400.0,
        )
        activity_span_days = max(
            0.0,
            (last_timestamp - first_timestamp).total_seconds() / 86400.0,
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
        len(transaction_hashes) / active_days
        if active_days > 0
        else 0.0
    )

    # -------------------------------------------------------------
    # Native ETH calculations
    # -------------------------------------------------------------
    total_eth_volume = sum(native_eth_values) if native_eth_values else 0.0
    average_eth_value = (total_eth_volume / len(native_eth_values)) if native_eth_values else 0.0
    median_eth_value = statistics.median(native_eth_values) if native_eth_values else 0.0

    # -------------------------------------------------------------
    # Phase 2B: Action Calculations
    # -------------------------------------------------------------
    borrow_count = 0
    deposit_count = 0
    repayment_count = 0
    withdrawal_count = 0
    liquidation_count = 0
    unknown_action_count = 0

    if defi_actions:
        normalized_wallet_lower = normalized_address.lower()
        for action in defi_actions:
            # Participant Verification: Only tally if the analyzed wallet is the relevant actor
            participants_lower = [p.lower() for p in action.participants]
            
            if not participants_lower or normalized_wallet_lower in participants_lower:
                if action.action == "deposit":
                    deposit_count += 1
                elif action.action == "withdrawal":
                    withdrawal_count += 1
                elif action.action == "borrow":
                    borrow_count += 1
                elif action.action == "repayment":
                    repayment_count += 1
                elif action.action == "liquidation":
                    liquidation_count += 1
                elif action.action == "unknown":
                    unknown_action_count += 1

    return WalletFeatures(
        wallet_address=normalized_address,
        unique_transaction_count=len(transaction_hashes),
        asset_transfer_event_count=len(raw_transfers),
        first_transaction_timestamp=first_timestamp_iso,
        last_transaction_timestamp=last_timestamp_iso,
        wallet_age_days=round(wallet_age_days, 2),
        activity_span_days=round(activity_span_days, 2),
        active_days=active_days,
        transactions_per_active_day=round(transactions_per_active_day, 2),
        
        # --- Phase 2A returned metrics ---
        protocols_used=sorted(list(protocols_interacted)),
        protocol_count=len(protocols_interacted),
        lending_protocol_count=len(lending_protocols),
        dex_protocol_count=len(dex_protocols),
        defi_transaction_count=len(defi_transaction_hashes),
        defi_active_days=len(defi_distinct_dates),
        
        # --- Phase 2B returned metrics ---
        borrow_count=borrow_count,
        deposit_count=deposit_count,
        repayment_count=repayment_count,
        withdrawal_count=withdrawal_count,
        liquidation_count=liquidation_count,
        unknown_action_count=unknown_action_count,

        total_native_eth_transfer_volume=round(total_eth_volume, 6),
        average_native_eth_transfer_value=round(average_eth_value, 6),
        median_native_eth_transfer_value=round(median_eth_value, 6),
        analysis_timestamp=analysis_timestamp_iso,
    )