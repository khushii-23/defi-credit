from typing import List, Dict, Any
from web3 import Web3
from app.models import DeFiAction

# Keccak256 hashes calculated directly from verified Aave V3 ABI strings
AAVE_V3_SIGNATURES = {
    "Supply": Web3.keccak(text="Supply(address,address,address,uint256,uint16)").hex(),
    "Withdraw": Web3.keccak(text="Withdraw(address,address,address,uint256)").hex(),
    "Borrow": Web3.keccak(text="Borrow(address,address,address,uint256,uint8,uint256,uint16)").hex(),
    "Repay": Web3.keccak(text="Repay(address,address,address,uint256,bool)").hex(),
    "LiquidationCall": Web3.keccak(text="LiquidationCall(address,address,address,uint256,uint256,address,bool)").hex(),
}

def extract_topic_address(topic: str) -> str:
    """Extract an Ethereum address from a 32-byte padded topic log."""
    if len(topic) >= 66:
        return Web3.to_checksum_address("0x" + topic[-40:])
    return ""

def decode_aave_v3_receipt(receipt: Dict[str, Any], aave_v3_pool_addresses: List[str]) -> List[DeFiAction]:
    """Decodes transaction receipt logs into structured Aave V3 DeFi actions."""
    actions = []
    tx_hash = receipt.get("transactionHash", "")
    if not tx_hash:
        return actions

    pool_addresses_lower = [addr.lower() for addr in aave_v3_pool_addresses]

    for log in receipt.get("logs", []):
        address = log.get("address", "").lower()
        
        # Methodological rule: Ignore unrelated logs (like standard ERC20 transfers).
        # Only parse events actually emitted by the Aave V3 Pool contract.
        if address not in pool_addresses_lower:
            continue 

        topics = log.get("topics", [])
        if not topics:
            continue

        event_sig = str(topics[0]).lower()
        participants = []
        action_type = "unknown"

        # Topic indices based on Aave V3 indexed ABI definitions
        if event_sig == AAVE_V3_SIGNATURES["Supply"].lower():
            action_type = "deposit"
            if len(topics) > 2:
                participants.append(extract_topic_address(topics[2])) # onBehalfOf
                
        elif event_sig == AAVE_V3_SIGNATURES["Withdraw"].lower():
            action_type = "withdrawal"
            if len(topics) > 2:
                participants.append(extract_topic_address(topics[2])) # user
            if len(topics) > 3:
                participants.append(extract_topic_address(topics[3])) # to
                
        elif event_sig == AAVE_V3_SIGNATURES["Borrow"].lower():
            action_type = "borrow"
            if len(topics) > 2:
                participants.append(extract_topic_address(topics[2])) # onBehalfOf
                
        elif event_sig == AAVE_V3_SIGNATURES["Repay"].lower():
            action_type = "repayment"
            if len(topics) > 2:
                participants.append(extract_topic_address(topics[2])) # user (borrower)
            if len(topics) > 3:
                participants.append(extract_topic_address(topics[3])) # repayer
                
        elif event_sig == AAVE_V3_SIGNATURES["LiquidationCall"].lower():
            action_type = "liquidation"
            if len(topics) > 3:
                participants.append(extract_topic_address(topics[3])) # user (liquidated)
        else:
            action_type = "unknown"

        # Deduplicate participants, filtering out empty strings
        participants = list(set([p for p in participants if p]))

        actions.append(DeFiAction(
            protocol="aave_v3",
            action=action_type,
            transaction_hash=tx_hash,
            participants=participants,
            evidence="log_signature_match" if action_type != "unknown" else "unsupported_relevant_event"
        ))

    return actions