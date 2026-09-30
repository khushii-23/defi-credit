import pytest
from datetime import datetime, timezone

from app.features import (
    extract_wallet_features,
    validate_ethereum_address,
)


def test_validate_ethereum_address_valid():
    address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

    assert validate_ethereum_address(address) == address.lower()


def test_validate_ethereum_address_invalid():
    with pytest.raises(ValueError):
        validate_ethereum_address(
            "0xInvalidAddress12345"
        )


def test_empty_transfer_history():
    address = (
        "0x0000000000000000000000000000000000000001"
    )

    analysis_time = datetime(
        2026,
        9,
        30,
        tzinfo=timezone.utc,
    )

    result = extract_wallet_features(
        address,
        [],
        analysis_timestamp=analysis_time,
    )

    assert result.unique_transaction_count == 0
    assert result.asset_transfer_event_count == 0
    assert result.active_days == 0
    assert result.wallet_age_days == 0.0
    assert result.total_native_eth_transfer_volume == 0.0
    assert result.analysis_timestamp == (
        "2026-09-30T00:00:00+00:00"
    )


def test_unique_transaction_count_is_not_transfer_event_count():

    address = (
        "0x0000000000000000000000000000000000000001"
    )

    raw_transfers = [

        {
            "hash": "0xabc",
            "asset": "ETH",
            "value": 1.0,
            "metadata": {
                "blockTimestamp":
                    "2026-01-01T10:00:00Z"
            },
        },

        {
            "hash": "0xabc",
            "asset": "DAI",
            "value": 100.0,
            "metadata": {
                "blockTimestamp":
                    "2026-01-01T10:00:00Z"
            },
        },

        {
            "hash": "0xdef",
            "asset": "ETH",
            "value": 2.0,
            "metadata": {
                "blockTimestamp":
                    "2026-01-02T12:00:00Z"
            },
        },
    ]

    analysis_time = datetime(
        2026,
        9,
        30,
        tzinfo=timezone.utc,
    )

    result = extract_wallet_features(
        address,
        raw_transfers,
        analysis_timestamp=analysis_time,
    )

    # 3 transfer events
    assert result.asset_transfer_event_count == 3

    # But only 2 blockchain transactions
    assert result.unique_transaction_count == 2

    assert result.active_days == 2

    assert result.transactions_per_active_day == 1.0


def test_native_eth_volume_only():

    address = (
        "0x0000000000000000000000000000000000000001"
    )

    raw_transfers = [

        {
            "hash": "0x111",
            "asset": "ETH",
            "value": 1.5,
            "metadata": {
                "blockTimestamp":
                    "2026-01-01T10:00:00Z"
            },
        },

        {
            "hash": "0x222",
            "asset": "ETH",
            "value": 2.5,
            "metadata": {
                "blockTimestamp":
                    "2026-01-02T12:00:00Z"
            },
        },

        {
            "hash": "0x333",
            "asset": "DAI",
            "value": 100.0,
            "metadata": {
                "blockTimestamp":
                    "2026-01-02T15:00:00Z"
            },
        },
    ]

    analysis_time = datetime(
        2026,
        9,
        30,
        tzinfo=timezone.utc,
    )

    result = extract_wallet_features(
        address,
        raw_transfers,
        analysis_timestamp=analysis_time,
    )

    assert result.total_native_eth_transfer_volume == 4.0

    assert result.average_native_eth_transfer_value == 2.0

    assert result.median_native_eth_transfer_value == 2.0


def test_analysis_timestamp_makes_wallet_age_reproducible():

    address = (
        "0x0000000000000000000000000000000000000001"
    )

    raw_transfers = [
        {
            "hash": "0xabc",
            "asset": "ETH",
            "value": 1.0,
            "metadata": {
                "blockTimestamp":
                    "2026-01-01T00:00:00Z"
            },
        }
    ]

    analysis_time = datetime(
        2026,
        1,
        11,
        tzinfo=timezone.utc,
    )

    result = extract_wallet_features(
        address,
        raw_transfers,
        analysis_timestamp=analysis_time,
    )

    assert result.wallet_age_days == 10.0