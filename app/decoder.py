"""Receipt-level decoder for Aave V3 Pool events (Ethereum mainnet).

Event layouts (from the Aave V3 IPool interface):
  Supply(address indexed reserve, address user, address indexed onBehalfOf,
         uint256 amount, uint16 indexed referralCode)
  Borrow(address indexed reserve, address user, address indexed onBehalfOf,
         uint256 amount, uint8 interestRateMode, uint256 borrowRate,
         uint16 indexed referralCode)
  Repay(address indexed reserve, address indexed user, address indexed repayer,
        uint256 amount, bool useATokens)
  LiquidationCall(address indexed collateralAsset, address indexed debtAsset,
        address indexed user, uint256 debtToCover,
        uint256 liquidatedCollateralAmount, address liquidator, bool receiveAToken)
"""
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Iterable, Optional
import requests

try:
    from Crypto.Hash import keccak

    def keccak256_hex(text: str) -> str:
        return "0x" + keccak.new(digest_bits=256, data=text.encode()).hexdigest()
except ImportError:
    # Fallback to web3.py keccak if pycryptodome is not installed
    try:
        from web3 import Web3
        def keccak256_hex(text: str) -> str:
            return Web3.keccak(text=text).hex()
    except ImportError:
        keccak256_hex = None

POOL = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"

SIGNATURES = {
    "Supply": "Supply(address,address,address,uint256,uint16)",
    "Borrow": "Borrow(address,address,address,uint256,uint8,uint256,uint16)",
    "Repay": "Repay(address,address,address,uint256,bool)",
    "LiquidationCall": "LiquidationCall(address,address,address,uint256,uint256,address,bool)",
}

# Precomputed hashes ensure the test suite works even without keccak libraries
PRECOMPUTED_TOPIC0 = {
    "Supply": "0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61",
    "Borrow": "0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0",
    "Repay": "0xa534c8dbe71f871f9f3530e97a74601fea17b426cae02e1c5aee42c96c784051",
    "LiquidationCall": "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286",
}

if keccak256_hex:
    TOPIC0 = {name: keccak256_hex(sig) for name, sig in SIGNATURES.items()}
else:
    TOPIC0 = PRECOMPUTED_TOPIC0

NAME_BY_TOPIC = {v: k for k, v in TOPIC0.items()}


@dataclass(frozen=True)
class Event:
    kind: str            # Supply | Borrow | Repay | LiquidationCall
    account: str         # economically affected account (lowercase)
    counterparty: str    # caller / payer / liquidator (ignored for scoring)
    asset: str           # reserve (debt asset for liquidations)
    amount_raw: int      # raw token units (debtToCover for liquidations)
    block: int
    tx_hash: str
    log_index: int
    timestamp: Optional[int] = None


def _addr_topic(t: str) -> str:
    return "0x" + t[-40:].lower()


def _word(data: str, i: int) -> int:
    h = data[2:] if data.startswith("0x") else data
    return int(h[i * 64:(i + 1) * 64], 16)


def _word_addr(data: str, i: int) -> str:
    return "0x" + format(_word(data, i), "064x")[-40:]


def decode_log(log: dict) -> Optional[Event]:
    """Decode one raw eth_getLogs entry. Returns None for unknown topics."""
    topics = log["topics"]
    kind = NAME_BY_TOPIC.get(topics[0].lower())
    if kind is None:
        return None
    data = log["data"]
    block = int(log["blockNumber"], 16) if isinstance(log["blockNumber"], str) else log["blockNumber"]
    li = int(log["logIndex"], 16) if isinstance(log["logIndex"], str) else log["logIndex"]
    common = dict(kind=kind, block=block, tx_hash=log["transactionHash"].lower(), log_index=li)

    if kind == "Supply":      # topics: reserve, onBehalfOf, referral | data: user, amount
        return Event(account=_addr_topic(topics[2]), counterparty=_word_addr(data, 0),
                     asset=_addr_topic(topics[1]), amount_raw=_word(data, 1), **common)
    if kind == "Borrow":      # topics: reserve, onBehalfOf, referral | data: user, amount, mode, rate
        return Event(account=_addr_topic(topics[2]), counterparty=_word_addr(data, 0),
                     asset=_addr_topic(topics[1]), amount_raw=_word(data, 1), **common)
    if kind == "Repay":       # topics: reserve, user, repayer | data: amount, useATokens
        return Event(account=_addr_topic(topics[2]), counterparty=_addr_topic(topics[3]),
                     asset=_addr_topic(topics[1]), amount_raw=_word(data, 0), **common)
    # LiquidationCall: topics: collateral, debt, user | data: debtToCover, collat, liquidator, receiveAToken
    return Event(account=_addr_topic(topics[3]), counterparty=_word_addr(data, 2),
                 asset=_addr_topic(topics[2]), amount_raw=_word(data, 0), **common)


# ---------- RPC Fetching & Timestamp Cache ----------

def _pad(addr: str) -> str:
    return "0x" + addr.lower().replace("0x", "").rjust(64, "0")


ACCOUNT_TOPIC_POS = {"Supply": 2, "Borrow": 2, "Repay": 2, "LiquidationCall": 3}
BLOCK_TIME_CACHE: dict[int, int] = {}


def rpc(url: str, method: str, params: list, retries: int = 5):
    for i in range(retries):
        r = requests.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=60)
        j = r.json()
        if "error" not in j:
            return j["result"]
        time.sleep(2 ** i)
    raise RuntimeError(f"RPC {method} failed: {j['error']}")


def rpc_batch(url: str, calls: list[dict]) -> list[dict]:
    """Execute a JSON-RPC batch call."""
    if not calls:
        return []
    r = requests.post(url, json=calls, timeout=60)
    return r.json()


def populate_block_timestamps(url: str, blocks: set[int]):
    """Batch fetch block timestamps for unique blocks."""
    missing = [b for b in blocks if b not in BLOCK_TIME_CACHE]
    for i in range(0, len(missing), 100):
        chunk = missing[i:i + 100]
        batch = [{
            "jsonrpc": "2.0",
            "id": idx,
            "method": "eth_getBlockByNumber",
            "params": [hex(b), False]
        } for idx, b in enumerate(chunk)]

        results = rpc_batch(url, batch)
        for res in results:
            b_num = int(res["result"]["number"], 16)
            ts = int(res["result"]["timestamp"], 16)
            BLOCK_TIME_CACHE[b_num] = ts


def fetch_logs(url: str, kind: str, start: int, end: int,
               wallets: Optional[Iterable[str]] = None, chunk: int = 2000) -> list[dict]:
    """eth_getLogs with adaptive chunking (halves the window on query limits)."""
    topics = [TOPIC0[kind]] + [None] * (ACCOUNT_TOPIC_POS[kind] - 1)
    if wallets:
        topics.append([_pad(w) for w in wallets])
    out, lo = [], start
    while lo <= end:
        hi = min(lo + chunk - 1, end)
        try:
            res = rpc(url, "eth_getLogs", [{"address": POOL, "topics": topics,
                                            "fromBlock": hex(lo), "toBlock": hex(hi)}])
            out += res
            lo = hi + 1
        except RuntimeError as err:
            err_msg = str(err).lower()
            if "10000" in err_msg or "limit" in err_msg or "timeout" in err_msg:
                if chunk <= 1:
                    raise
                chunk //= 2
            else:
                raise
    return out


def is_contract(url: str, addr: str) -> bool:
    return rpc(url, "eth_getCode", [addr, "latest"]) not in ("0x", "0x0")


def block_timestamp(url: str, block: int) -> int:
    if block in BLOCK_TIME_CACHE:
        return BLOCK_TIME_CACHE[block]
    ts = int(rpc(url, "eth_getBlockByNumber", [hex(block), False])["timestamp"], 16)
    BLOCK_TIME_CACHE[block] = ts
    return ts