import pytest
from app.protocol_behaviour import decode_aave_v3_receipt, AAVE_V3_SIGNATURES
from app.features import extract_wallet_features
from app.models import DeFiAction

# The address of the Aave V3 Pool we want to test
AAVE_POOL = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"
# Mock Wallet Address (Padded to 32 bytes for log simulation)
WALLET_ADDRESS = "0x1111111111111111111111111111111111111111"
PADDED_WALLET = f"0x000000000000000000000000{WALLET_ADDRESS[2:]}"

def create_mock_receipt(logs: list) -> dict:
    return {
        "transactionHash": "0xtxhash",
        "logs": logs
    }

def test_aave_v3_supply_decode():
    receipt = create_mock_receipt([{
        "address": AAVE_POOL,
        # Supply: signature, reserve, onBehalfOf, referralCode
        "topics": [
            AAVE_V3_SIGNATURES["Supply"],
            "0xreserve...", 
            PADDED_WALLET, 
            "0x00"
        ]
    }])
    
    actions = decode_aave_v3_receipt(receipt, [AAVE_POOL])
    
    assert len(actions) == 1
    assert actions[0].action == "deposit"
    assert actions[0].protocol == "aave_v3"
    assert actions[0].evidence == "log_signature_match"
    assert actions[0].participants == [WALLET_ADDRESS]

def test_unrelated_erc20_log_is_ignored():
    receipt = create_mock_receipt([{
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", # USDC Contract, NOT Aave Pool
        "topics": [AAVE_V3_SIGNATURES["Supply"]] # Fake topic, but wrong address
    }])
    
    actions = decode_aave_v3_receipt(receipt, [AAVE_POOL])
    assert len(actions) == 0 # Methodological rule: Ignore unrelated contracts

def test_unknown_relevant_aave_event():
    receipt = create_mock_receipt([{
        "address": AAVE_POOL,
        "topics": [
            "0x9999999999999999999999999999999999999999999999999999999999999999", # Unknown event from Aave pool (e.g. FlashLoan)
        ]
    }])
    
    actions = decode_aave_v3_receipt(receipt, [AAVE_POOL])
    assert len(actions) == 1
    assert actions[0].action == "unknown"
    assert actions[0].evidence == "unsupported_relevant_event"

def test_participant_matching_in_features():
    my_wallet = WALLET_ADDRESS
    other_wallet = "0x2222222222222222222222222222222222222222"
    
    actions = [
        # I borrowed
        DeFiAction(protocol="aave_v3", action="borrow", transaction_hash="0x1", participants=[my_wallet], evidence="log"),
        # Someone else borrowed
        DeFiAction(protocol="aave_v3", action="borrow", transaction_hash="0x2", participants=[other_wallet], evidence="log"),
        # I deposited
        DeFiAction(protocol="aave_v3", action="deposit", transaction_hash="0x3", participants=[my_wallet], evidence="log"),
    ]
    
    # Run feature extraction using empty transfers, just testing action ingestion
    features = extract_wallet_features(my_wallet, [], defi_actions=actions)
    
    # I should have 1 borrow and 1 deposit, ignoring the other wallet's action
    assert features.borrow_count == 1
    assert features.deposit_count == 1