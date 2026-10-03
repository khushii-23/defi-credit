import os
import json
from dotenv import load_dotenv
from web3 import Web3

# Load Alchemy Key
load_dotenv()
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
if not ALCHEMY_API_KEY or ALCHEMY_API_KEY == "demo":
    raise ValueError("Valid ALCHEMY_API_KEY required in .env")

# Connect to Ethereum Mainnet
w3 = Web3(Web3.HTTPProvider(f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"))
print(f"Connected to Ethereum Mainnet. Latest Block: {w3.eth.block_number}")

# Aave V3 Pool Contract & Event Signatures
POOL = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"
# keccak256("Borrow(address,address,address,uint256,uint8,uint256,uint16)")
BORROW_TOPIC = "0xb3d084820fb1a9decff51f27eddfa53d2ce99aa0d585b52045c89006fa129e05"
# keccak256("LiquidationCall(address,address,address,uint256,uint256,address,bool)")
LIQUIDATION_TOPIC = "0xe428a9b7027581b2fb9820f4c3997f75ebed75168fc33221ed3e00b2176b6b7a"

latest_block = w3.eth.block_number
# Scan the last ~7 days of Ethereum blocks (approx 50,000 blocks)
start_block = latest_block - 50000 
CHUNK_SIZE = 5000  # Chunk to avoid Alchemy free-tier block range limits

liquidated_wallets = set()
healthy_wallets = set()

print(f"Scanning blocks {start_block} to {latest_block} in chunks of {CHUNK_SIZE}...")

for i in range(start_block, latest_block, CHUNK_SIZE):
    end_block = min(i + CHUNK_SIZE, latest_block)
    
    # 1. Fetch Liquidations
    liq_logs = w3.eth.get_logs({
        'address': POOL,
        'topics': [LIQUIDATION_TOPIC],
        'fromBlock': i,
        'toBlock': end_block
    })
    
    for log in liq_logs:
        # In LiquidationCall, the 4th topic (index 3) is the user address
        if len(log['topics']) > 3:
            user_address = "0x" + log['topics'][3].hex()[-40:]
            liquidated_wallets.add(Web3.to_checksum_address(user_address))

    # 2. Fetch Borrows
    borrow_logs = w3.eth.get_logs({
        'address': POOL,
        'topics': [BORROW_TOPIC],
        'fromBlock': i,
        'toBlock': end_block
    })
    
    for log in borrow_logs:
        # In Borrow, the 3rd topic (index 2) is the user address
        if len(log['topics']) > 2:
            user_address = "0x" + log['topics'][2].hex()[-40:]
            addr = Web3.to_checksum_address(user_address)
            # Only add to healthy if they haven't also been liquidated recently
            if addr not in liquidated_wallets:
                healthy_wallets.add(addr)
                
    print(f"  Scanned up to block {end_block}...")

# Format for our evaluation script (Cap at 25 each for API speed during evaluation)
cohorts = {
    "healthy_borrowers": [
        {"address": a, "label": "Recent Aave V3 Borrower"} for a in list(healthy_wallets)[:25]
    ],
    "liquidated_borrowers": [
        {"address": a, "label": "Recent Aave V3 Liquidation"} for a in list(liquidated_wallets)[:25]
    ],
    "inactive_wallets": [
        { "address": "0x0000000000000000000000000000000000000001", "label": "Precompile / Burn Address" },
        { "address": "0x000000000000000000000000000000000000dead", "label": "Dead Burn Address" }
    ]
}

# Save directly to our existing cohorts file
with open("scripts/cohorts.json", "w") as f:
    json.dump(cohorts, f, indent=2)

print("\n" + "="*50)
print(f"EXTRACTION COMPLETE!")
print(f"Saved {len(cohorts['healthy_borrowers'])} Healthy Wallets")
print(f"Saved {len(cohorts['liquidated_borrowers'])} Liquidated Wallets")
print("Target file updated: scripts/cohorts.json")
print("="*50)