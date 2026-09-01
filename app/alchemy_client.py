from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from alchemy import Alchemy, Network
from alchemy.exceptions import AlchemyError
from web3 import Web3

from app.config import MAX_TRANSFER_PAGES, TRANSFER_PAGE_SIZE
from app.protocols import PROTOCOL_BY_ADDRESS
from app.scoring import WalletMetrics

# String categories: alchemy-sdk's ERC20 enum member is a 1-tuple because of a trailing comma.
TRANSFER_CATEGORIES = ["external", "internal", "erc20"]

NETWORK_BY_NAME = {
    "eth-mainnet": Network.ETH_MAINNET,
    "eth_mainnet": Network.ETH_MAINNET,
}


class OracleDataError(Exception):
    """Raised when Alchemy cannot return wallet history."""


class NewWalletError(Exception):
    """Raised when the address has no on-chain history."""

    def __init__(self, address: str) -> None:
        self.address = address
        super().__init__(f"Wallet {address} has no on-chain history")


def _parse_timestamp(value: str) -> datetime:
    cleaned = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(cleaned)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _transfer_counterparty(transfer: Any, wallet: str) -> Optional[str]:
    wallet_lc = wallet.lower()
    frm = getattr(transfer, "frm", "") or ""
    to = getattr(transfer, "to", None) or ""
    if frm.lower() == wallet_lc and to:
        return to
    if to.lower() == wallet_lc and frm:
        return frm
    return to or frm or None


def _iter_transfers(payload: dict) -> Iterable[Any]:
    return payload.get("transfers") or []


class AlchemyOracle:
    def __init__(self, api_key: str, network: Network = Network.ETH_MAINNET) -> None:
        self.client = Alchemy(api_key=api_key, network=network, max_retries=3)

    def _first_transfer_time(
        self, address: str, *, inbound: bool
    ) -> Optional[datetime]:
        kwargs: dict[str, Any] = {
            "category": TRANSFER_CATEGORIES,
            "with_metadata": True,
            "from_block": "0x0",
            "order": "asc",
            "max_count": 1,
            "exclude_zero_value": False,
        }
        if inbound:
            kwargs["to_address"] = address
        else:
            kwargs["from_address"] = address

        try:
            result = self.client.core.get_asset_transfers(**kwargs)
        except AlchemyError as exc:
            raise OracleDataError(str(exc)) from exc

        transfers = list(_iter_transfers(result))
        if not transfers:
            return None
        metadata = getattr(transfers[0], "metadata", None)
        ts = getattr(metadata, "block_timestamp", None) if metadata else None
        if not ts:
            return None
        return _parse_timestamp(ts)

    def _paged_transfers(self, address: str, *, inbound: bool) -> list[Any]:
        collected: list[Any] = []
        page_key: Optional[str] = None
        kwargs_base: dict[str, Any] = {
            "category": TRANSFER_CATEGORIES,
            "with_metadata": False,
            "from_block": "0x0",
            "order": "asc",
            "max_count": TRANSFER_PAGE_SIZE,
            "exclude_zero_value": False,
        }
        if inbound:
            kwargs_base["to_address"] = address
        else:
            kwargs_base["from_address"] = address

        for _ in range(MAX_TRANSFER_PAGES):
            kwargs = dict(kwargs_base)
            if page_key:
                kwargs["page_key"] = page_key
            try:
                result = self.client.core.get_asset_transfers(**kwargs)
            except AlchemyError as exc:
                raise OracleDataError(str(exc)) from exc
            page = list(_iter_transfers(result))
            collected.extend(page)
            page_key = result.get("page_key")
            if not page_key:
                break
        return collected

    def fetch_metrics(self, address: str) -> WalletMetrics:
        checksum = Web3.to_checksum_address(address)

        try:
            nonce = self.client.core.get_transaction_count(checksum)
        except Exception as exc:
            raise OracleDataError(f"Failed to read transaction count: {exc}") from exc

        first_out = self._first_transfer_time(checksum, inbound=False)
        first_in = self._first_transfer_time(checksum, inbound=True)
        firsts = [ts for ts in (first_out, first_in) if ts is not None]

        outbound = self._paged_transfers(checksum, inbound=False)
        inbound = self._paged_transfers(checksum, inbound=True)
        transfers = outbound + inbound

        unique_hashes = {getattr(t, "hash", None) for t in transfers}
        unique_hashes.discard(None)
        tx_count = max(int(nonce), len(unique_hashes))

        if not firsts and tx_count == 0:
            raise NewWalletError(checksum)

        if firsts:
            age_days = (datetime.now(timezone.utc) - min(firsts)).total_seconds() / 86400
        else:
            age_days = 0.0

        protocols: set[str] = set()
        defi_hashes: set[str] = set()
        for transfer in transfers:
            counterparty = _transfer_counterparty(transfer, checksum)
            if not counterparty:
                continue
            try:
                keyed = Web3.to_checksum_address(counterparty)
            except ValueError:
                continue
            protocol = PROTOCOL_BY_ADDRESS.get(keyed)
            if protocol:
                protocols.add(protocol)
                tx_hash = getattr(transfer, "hash", None)
                if tx_hash:
                    defi_hashes.add(tx_hash)

        return WalletMetrics(
            account_age_days=max(age_days, 0.0),
            transaction_count=tx_count,
            defi_interaction_count=len(defi_hashes),
            protocols_used=tuple(sorted(protocols)),
        )
