import json
import os
from dotenv import load_dotenv
from app.decoder import fetch_logs, decode_log, populate_block_timestamps, BLOCK_TIME_CACHE
from app.pricing import raw_to_usd

# Load environment variables
load_dotenv()
ALCHEMY_URL = os.getenv("ALCHEMY_URL")

def main():
    if not ALCHEMY_URL:
        raise ValueError("ALCHEMY_URL not found in .env. Please add it.")

    # 1. Load the pilot cohorts
    with open("scripts/cohorts.json", "r") as f:
        cohorts = json.load(f)

    # Flatten all wallets to lowercase for exact matching
    all_wallets = []
    for group in cohorts.values():
        all_wallets.extend([w.lower() for w in group])

    print(f"Loaded {len(all_wallets)} pilot wallets from cohorts.json")

    # 2. Define block range (approx last 12 months for the pilot)
    END_BLOCK = 26124839
    START_BLOCK = END_BLOCK - 2500000 
    print(f"Fetching logs from block {START_BLOCK} to {END_BLOCK}...")

    all_decoded_events = []

    # 3. Fetch logs for each event type using our adaptive decoder
    event_types = ["Supply", "Borrow", "Repay", "LiquidationCall"]
    
    for kind in event_types:
        print(f"Fetching {kind} events...")
        # fetch_logs will automatically halve the chunk size if Alchemy throws a limit error
        raw_logs = fetch_logs(
            url=ALCHEMY_URL,
            kind=kind,
            start=START_BLOCK,
            end=END_BLOCK,
            wallets=all_wallets,
            chunk=100000 
        )
        
        # Decode logs
        for log in raw_logs:
            event = decode_log(log)
            if event and event.account in all_wallets:
                all_decoded_events.append(event)

    print(f"Decoded {len(all_decoded_events)} relevant events.")

    # 4. Batch fetch block timestamps to avoid thousands of individual RPC calls
    unique_blocks = {e.block for e in all_decoded_events}
    print(f"Batch fetching timestamps for {len(unique_blocks)} unique blocks...")
    populate_block_timestamps(ALCHEMY_URL, unique_blocks)

    # 5. Format for the scoring engine and apply USD conversions
    final_events = []
    for e in all_decoded_events:
        ts = BLOCK_TIME_CACHE.get(e.block, 0)
        usd_val = raw_to_usd(e.asset, e.amount_raw)
        
        final_events.append({
            "kind": e.kind,
            "ts": ts,
            "asset": e.asset,
            "usd": usd_val,
            "account": e.account
        })

    # 6. Save to disk for evaluate_cohorts.py
    out_file = "scripts/extracted_events.json"
    with open(out_file, "w") as f:
        json.dump(final_events, f, indent=2)
        
    print(f"Successfully saved {len(final_events)} events to {out_file}. Ready for evaluation.")

if __name__ == "__main__":
    main()