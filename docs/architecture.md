# DeFi Credit Scoring — System Architecture

## 1. Overview

This document describes the current and planned architecture of the DeFi Credit Scoring project.

### Project

**DeFi Credit Scoring: An Explainable On-Chain Reputation System for Risk-Adjusted Lending**

The system is intended to analyze historical blockchain activity associated with a wallet, extract behavioral and risk-related features, and generate an explainable reputation/credit score that can potentially support risk-adjusted DeFi lending.

The architecture is designed to keep blockchain data collection, data processing, scoring, API functionality, and future presentation layers separated.

---

# 2. High-Level Architecture

The intended system architecture is:

```text
                    ┌──────────────────────┐
                    │      Blockchain      │
                    │   On-Chain Activity  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Alchemy API      │
                    │ Blockchain Data Layer│
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Data Processing    │
                    │ & Data Normalization │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Feature Extraction  │
                    │ Wallet-Level Features│
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Risk / Behavior      │
                    │ Analysis             │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Scoring Engine     │
                    │ Credit/Reputation    │
                    │ Score Generation     │
                    └──────────┬───────────┘
                               │
                     ┌─────────┴─────────┐
                     ▼                   ▼
          ┌──────────────────┐  ┌──────────────────┐
          │ Explainability   │  │ Risk Assessment  │
          │ / Score Factors  │  │ / Classification  │
          └────────┬─────────┘  └────────┬─────────┘
                   │                     │
                   └──────────┬──────────┘
                              ▼
                    ┌──────────────────────┐
                    │     FastAPI API      │
                    │    Backend Layer     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Future Web Dashboard │
                    │ / External Consumer  │
                    └──────────────────────┘