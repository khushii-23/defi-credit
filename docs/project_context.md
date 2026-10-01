# DeFi Credit Scoring — Project Context

## 1. Project Overview

### Project Title
DeFi Credit Scoring: An Explainable On-Chain Reputation System for Risk-Adjusted Lending

### Project Type
MSc Computer Science Research Project

### Core Research Problem
Traditional DeFi lending systems primarily rely on collateral to manage lending risk, limiting the ability to distinguish between borrowers based on their historical on-chain behavior. This project investigates whether historical blockchain activity can be analyzed to generate an explainable reputation/credit score.

## 2. Current Project Status
**Phase:** Backend Feature Engineering (Task 2: Protocol-Specific Behaviour)
**Completion:** ~40% (Task 1 Complete, Task 2 Core Logic Complete)

### Implemented Architecture & Features
The pipeline follows a strictly decoupled model:
1. **On-Chain Asset Transfer Ingestion:** Alchemy RPC API (`get_asset_transfers`).
2. **Phase 2A (Protocol Identification):** Cross-references transfer addresses against a typed `ProtocolCategory` registry (LENDING, DEX, YIELD) to defensibly track `protocols_used`, `lending_protocol_count`, and `defi_transaction_count`.
3. **Phase 2B (Log-Based Action Detection):** A modular decoding layer (`protocol_behaviour.py`) that strictly uses verified Keccak256 event signatures (currently Aave V3) to parse transaction receipts.
4. **Stateless Feature Engineering:** `app/features.py` aggregates both transfer-derived and log-derived metrics without making live RPC calls.

### Implemented Features (Wallet-Level)
*   `unique_transaction_count`, `asset_transfer_event_count`, `wallet_age_days`, `active_days`
*   `total_native_eth_transfer_volume`
*   `protocols_used`, `protocol_count`, `lending_protocol_count`, `dex_protocol_count`
*   `defi_transaction_count`, `defi_active_days`
*   **Tier 2 (Log-Derived):** `borrow_count`, `deposit_count`, `repayment_count`, `withdrawal_count`, `liquidation_count`, `unknown_action_count`.

## 3. Methodological Rules & Research Constraints
*   **Transfers != Transactions:** A single blockchain transaction may generate multiple asset-transfer events. These are explicitly deduplicated.
*   **Interactions != Actions:** A transfer to a protocol contract (e.g., Aave) is recorded as a *Protocol Interaction*. It is **never** assumed to be a specific financial action (e.g., a "deposit" or "repay"). 
*   **Evidence-Based Detection:** Specific actions are only counted when corroborated by verifiable smart contract event logs (receipt topics) matching official protocol ABIs.
*   **Participant Verification:** Actions are only credited if the analyzed wallet is the relevant actor (e.g., `user` or `onBehalfOf`).

## 4. Next Immediate Steps (Task 2 Completion)
*   Implement `fetch_transaction_receipt(tx_hash)` in `app/alchemy_client.py` to fetch logs for identified DeFi transactions.
*   Wire the receipt fetching and decoder logic into the FastAPI route in `app/main.py`.