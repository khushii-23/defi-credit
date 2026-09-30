import pytest
from datetime import datetime, timezone
from app.features import extract_wallet_features

def test_defi_feature_extraction_deduplicates_transactions():
    address = "0x0000000000000000000000000000000000000001"
    
    # Aave V2 LendingPool
    aave_pool = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
    # Uniswap V2 Router
    uni_router = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"

    raw_transfers = [
        # Tx 1: Sent ETH to Uniswap Router (DEX)
        {
            "hash": "0xabc",
            "to": uni_router,
            "asset": "ETH",
            "metadata": {"blockTimestamp": "2026-01-01T10:00:00Z"},
        },
        # Tx 1: Received token back from Uniswap Router (Same tx hash)
        {
            "hash": "0xabc",
            "from": uni_router,
            "asset": "USDC",
            "metadata": {"blockTimestamp": "2026-01-01T10:00:00Z"},
        },
        # Tx 2: Sent USDC to Aave (LENDING)
        {
            "hash": "0xdef",
            "to": aave_pool,
            "asset": "USDC",
            "metadata": {"blockTimestamp": "2026-01-02T12:00:00Z"},
        }
    ]

    analysis_time = datetime(2026, 9, 30, tzinfo=timezone.utc)
    result = extract_wallet_features(address, raw_transfers, analysis_time)

    # Assert methodology constraints
    assert result.asset_transfer_event_count == 3
    assert result.unique_transaction_count == 2
    
    # Phase 2A Assertions
    assert result.defi_transaction_count == 2 # '0xabc' and '0xdef'
    assert result.protocol_count == 2
    assert "aave" in result.protocols_used
    assert "uniswap" in result.protocols_used
    
    # Category separation
    assert result.lending_protocol_count == 1
    assert result.dex_protocol_count == 1
    assert result.defi_active_days == 2

def test_non_defi_transfers_do_not_inflate_metrics():
    address = "0x0000000000000000000000000000000000000001"
    random_address = "0x9999999999999999999999999999999999999999"

    raw_transfers = [
        {
            "hash": "0x123",
            "to": random_address,
            "metadata": {"blockTimestamp": "2026-01-01T10:00:00Z"},
        }
    ]

    result = extract_wallet_features(address, raw_transfers)

    assert result.unique_transaction_count == 1
    assert result.defi_transaction_count == 0
    assert result.protocol_count == 0