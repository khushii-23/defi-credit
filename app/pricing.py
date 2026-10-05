"""Token metadata and USD price resolver for Aave V3 core reserves."""
from __future__ import annotations
from typing import Optional

# Mainnet asset mappings: address.lower() -> (symbol, decimals, fallback_usd)
ASSET_META = {
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": ("USDC", 6, 1.0),
    "0xdac17f958d2ee523a2206206994597c13d831ec7": ("USDT", 6, 1.0),
    "0x6b175474e89094c44da98b954eedeac495271d0f": ("DAI", 18, 1.0),
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": ("WETH", 18, 3000.0),
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": ("WBTC", 8, 65000.0),
    "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9": ("AAVE", 18, 150.0),
}

def raw_to_usd(asset_addr: str, amount_raw: int, price_usd: Optional[float] = None) -> float:
    addr = asset_addr.lower()
    if addr not in ASSET_META:
        return float(amount_raw) / 1e18
    
    symbol, decimals, fallback_price = ASSET_META[addr]
    token_units = amount_raw / (10 ** decimals)
    unit_price = price_usd if price_usd is not None else fallback_price
    return token_units * unit_price