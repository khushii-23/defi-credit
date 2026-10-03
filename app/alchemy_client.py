from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from alchemy import Alchemy, Network
from alchemy.exceptions import AlchemyError
from web3 import Web3

from app.config import MAX_TRANSFER_PAGES, TRANSFER_PAGE_SIZE

TRANSFER_CATEGORIES = ["external", "internal", "erc20"]

class OracleDataError(Exception):
    """Raised when Alchemy cannot return wallet history."""

def _iter_transfers(payload: dict) -> Iterable[Any]:
    return payload.get("transfers") or []

class AlchemyOracle:
    def __init__(self, api_key: str, network: Network = Network.ETH_MAINNET) -> None:
        self.client = Alchemy(api_key=api_key, network=network, max_retries=3)

    def _paged_transfers(self, address: str, *, inbound: bool) -> list[Any]:
        collected: list[Any] = []
        page_key: Optional[str] = None
        kwargs_base: dict[str, Any] = {
            "category": TRANSFER_CATEGORIES,
            "with_metadata": True,
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

    def fetch_asset_transfers(self, address: str) -> list[dict]:
        checksum = Web3.to_checksum_address(address)
        outbound = self._paged_transfers(checksum, inbound=False)
        inbound = self._paged_transfers(checksum, inbound=True)
        transfers = outbound + inbound
        normalized_transfers = []
        
        for transfer in transfers:
            metadata = getattr(transfer, "metadata", None)
            block_timestamp = None
            if metadata:
                block_timestamp = getattr(metadata, "block_timestamp", None)
            normalized_transfers.append({
                "hash": getattr(transfer, "hash", None),
                "from": getattr(transfer, "frm", None),
                "to": getattr(transfer, "to", None),
                "asset": getattr(transfer, "asset", None),
                "value": getattr(transfer, "value", None),
                "category": getattr(transfer, "category", None),
                "metadata": {"blockTimestamp": block_timestamp},
            })
        return normalized_transfers

    def fetch_transaction_receipt(self, tx_hash: str) -> Optional[dict]:
        """Fetch a single transaction receipt and convert to a normalized dictionary."""
        try:
            receipt = self.client.core.get_transaction_receipt(tx_hash)
            if not receipt:
                return None
            
            logs = getattr(receipt, "logs", [])
            normalized_logs = []
            
            for log in logs:
                normalized_topics = []
                for topic in getattr(log, "topics", []):
                    # Handle Web3 HexBytes gracefully for our stateless decoder
                    if hasattr(topic, "hex"):
                        normalized_topics.append(topic.hex())
                    else:
                        normalized_topics.append(str(topic))

                normalized_logs.append({
                    "address": getattr(log, "address", ""),
                    "topics": normalized_topics,
                    "data": getattr(log, "data", ""),
                })
            
            return {
                "transactionHash": getattr(receipt, "transactionHash", tx_hash),
                "logs": normalized_logs
            }
            
        except AlchemyError as exc:
            raise OracleDataError(f"Failed to fetch receipt for {tx_hash}: {exc}") from exc
        except Exception as exc:
            raise OracleDataError(f"Provider error fetching receipt for {tx_hash}: {exc}") from exc