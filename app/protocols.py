"""Canonical Ethereum mainnet DeFi contracts used for interaction counting."""

from web3 import Web3

# Protocol name -> list of checksummed contract addresses (routers, pools, vaults).
DEFI_PROTOCOLS: dict[str, list[str]] = {
    "uniswap": [
        "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",  # V2 Router
        "0xE592427A0AEce92De3Edee1F18E0157C05861564",  # V3 SwapRouter
        "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",  # SwapRouter02
        "0x3fC91A3afd70395Cc0961486e16744F775dE934D",  # Universal Router
        "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",  # V2 Factory
        "0x1F98431c8aD98523631AE4a59f267346ea31F984",  # V3 Factory
    ],
    "aave": [
        "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9",  # V2 LendingPool
        "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",  # V3 Pool
        "0x2f39d218133AFaB8F2B819B1066c7E434Ad94E9e",  # V3 Pool Addresses Provider
    ],
    "compound": [
        "0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B",  # Comptroller
        "0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5",  # cETH
        "0xc3d688B66703497DAA19211EEd0468b4d5E0d3F8",  # Comet USDC
        "0xA17581A9E3356d9A858b789D68B4d866e593aE94",  # Comet WETH
    ],
    "maker": [
        "0x9759A6Ac90977b93B58547b4A71c78317f391A28",  # Join DAI
        "0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B",  # Vat
        "0x373238337Bfe1146fb43CdC72ff81517AD956Bd6",  # DSR Manager
        "0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4",  # Proxy Registry
    ],
    "curve": [
        "0x99a58482EE7e1B2622a25D36DD65B09548e0836f",  # Router
        "0x0000000022D53366457F9d5E68Ec105046FC4383",  # Address Provider
        "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",  # 3pool
    ],
    "lido": [
        "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",  # stETH
        "0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1",  # Withdrawal Queue
        "0x888888888889758F76e7103c6CbF23ABbF58F946",  # CSM
    ],
    "oneinch": [
        "0x1111111254EEB25477B68fb85Ed929f73A960582",  # Aggregation Router v5
        "0x111111125421cA6dc452d289314280a0f8842A65",  # Aggregation Router v6
    ],
    "sushiswap": [
        "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",  # Router
    ],
    "balancer": [
        "0xBA12222222228d8Ba445958a75a0704d566BF2C8",  # Vault
    ],
    "spark": [
        "0xC13e21B648A5Ee794902342038FF3aDAB66BE987",  # Pool
    ],
    "morpho": [
        "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb",  # Morpho Blue
    ],
    "yearn": [
        "0x50c1a2eA0a861A967D9d0FFE2AE4012c2E053804",  # Registry
    ],
}


def build_protocol_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for name, addresses in DEFI_PROTOCOLS.items():
        for address in addresses:
            lookup[Web3.to_checksum_address(address)] = name
    return lookup


PROTOCOL_BY_ADDRESS = build_protocol_lookup()
