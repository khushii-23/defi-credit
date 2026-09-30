# tests/test_features.py
import pytest
from datetime import datetime, timezone
from app.features import extract_wallet_features, validate_ethereum_address, WalletFeatures

def test_validate_ethereum_address_valid():
    addr = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    assert validate_ethereum_address(addr) == addr.lower()

def test_validate_ethereum_address_invalid():
    with pytest.raises(ValueError):
        validate_ethereum_address("0xInvalidAddress12345")

def test_extract_wallet_features_empty():
    addr = "0x0000000000000000000000000000000000000000"
    res = extract_wallet_features(addr, [])
    assert res.wallet_address == addr
    assert res.transaction_count == 0
    assert res.active_days == 0
    assert res.total_transaction_volume_eth == 0.0
    assert res.failed_transaction_ratio == 0.0

def test_extract_wallet_features_calculation():
    addr = "0x0000000000000000000000000000000000000001"
    raw = [
        {
            "category": "external",
            "asset": "ETH",
            "value": 1.5,
            "metadata": {"blockTimestamp": "2026-01-01T10:00:00Z"}
        },
        {
            "category": "external",
            "asset": "ETH",
            "value": 2.5,
            "metadata": {"blockTimestamp": "2026-01-02T12:00:00Z"}
        },
        {
            "category": "external",
            "asset": "DAI",
            "value": 100.0,
            "metadata": {"blockTimestamp": "2026-01-02T15:00:00Z"}
        }
    ]
    res = extract_wallet_features(addr, raw)
    assert res.transaction_count == 3
    assert res.active_days == 2
    assert res.transactions_per_active_day == 1.5
    assert res.total_transaction_volume_eth == 4.0
    assert res.average_transaction_value_eth == 2.0
    assert res.median_transaction_value_eth == 2.0
    assert res.first_transaction_timestamp.startswith("2026-01-01")
    assert res.last_transaction_timestamp.startswith("2026-01-02")