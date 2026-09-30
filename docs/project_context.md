# DeFi Credit Scoring — Project Context

## 1. Project Overview

### Project Title
DeFi Credit Scoring: An Explainable On-Chain Reputation System for Risk-Adjusted Lending

### Project Type
MSc Computer Science Research Project

### Domain
- Decentralized Finance (DeFi)
- Blockchain Analytics
- Credit/Risk Scoring
- Machine Learning
- Explainable AI
- Smart Contract / On-Chain Data Analysis

### Core Research Problem

Traditional DeFi lending systems primarily rely on collateral to manage lending risk. This limits the ability to distinguish between borrowers based on their historical on-chain behavior.

This project investigates whether historical blockchain activity of a wallet can be analyzed to generate an explainable reputation/credit score that can complement collateral-based lending decisions.

The system is intended to analyze wallet behavior, extract meaningful features, assess risk, and generate a score that can be interpreted by users or integrated into a lending workflow.

---

## 2. Main Objective

The main objective is to develop an explainable on-chain reputation and credit scoring system that:

1. Collects relevant blockchain wallet activity.
2. Processes and structures transaction data.
3. Extracts behavioral and financial features.
4. Calculates risk-related indicators.
5. Generates a wallet-level credit/reputation score.
6. Provides explanations for the generated score.
7. Can potentially be used to support risk-adjusted DeFi lending.

---

## 3. Current Project Status

### Current Phase

Backend foundation / initial implementation.

The repository currently contains the initial backend structure, configuration, blockchain API client, protocol definitions, scoring logic, API entry point, and basic tests.

This is an evolving research project. Features should not be considered complete unless they are implemented in the repository.

---

## 4. Current Repository Structure

```text
defi-credit/
│
├── app/
│   ├── alchemy_client.py
│   ├── config.py
│   ├── main.py
│   ├── models.py
│   ├── protocols.py
│   └── scoring.py
│
├── tests/
│   ├── test_api.py
│   └── test_scoring.py
│
├── docs/
│   ├── PROJECT_CONTEXT.md
│   └── DECISIONS.md
│
├── .env.example
├── .gitignore
├── pytest.ini
└── requirements.txt


# Project Context & Progress

## Pipeline Architecture (Task 1 Complete)
The pipeline now follows a strictly decoupled model:
1. Address Validation & Normalization
2. On-Chain Asset Transfer Ingestion (Alchemy RPC API)
3. Feature Engineering (`app/features.py`)
4. Output Validation via Pydantic (`WalletFeatures`)
5. FastAPI Endpoint Ingestion (`GET /wallet/{wallet_address}/features`)

## Derived Feature Set
- `wallet_address`
- `transaction_count`
- `first_transaction_timestamp` / `last_transaction_timestamp`
- `wallet_age_days`
- `activity_span_days`
- `active_days`
- `transactions_per_active_day`
- `total_transaction_volume_eth`
- `average_transaction_value_eth`
- `median_transaction_value_eth`
- `successful_transaction_count`
- `failed_transaction_count`
- `failed_transaction_ratio`

## Limitations
- Asset transfer endpoints do not reflect non-state-changing zero-value failed contract executions unless combined with raw transaction receipts.
- Token values are currently calculated in native ETH terms; USD conversion requires oracle/price indexer integration.