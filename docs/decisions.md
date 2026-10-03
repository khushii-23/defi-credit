
---

# `docs/DECISIONS.md`

This one should be much more focused. **Don't put every tiny coding decision here.** Use it for decisions that future GPTs need to understand so they don't randomly change your architecture or research methodology.

```markdown
# Project Decisions

This document records important technical, architectural, and research decisions made during the development of the DeFi Credit Scoring project.

The purpose is to preserve project reasoning across development sessions and when working with different AI assistants.

---

## Decision Log

---

## D001 — Use GitHub as the Project Source of Truth

**Date:** 2026-09-30

**Decision:**

The GitHub repository is the authoritative source for the current project implementation.

Repository:

`https://github.com/khushii-23/defi-credit`

**Reason:**

The project may be developed with different GPTs or development sessions. Keeping the implementation in GitHub allows different assistants to inspect the latest code instead of relying on previous conversation history.

**Implication:**

AI assistants should inspect the current repository before making assumptions about the implementation.

---

## D002 — Maintain a Dedicated Project Context Document

**Date:** 2026-09-30

**Decision:**

Maintain project-level context in:

text
docs/PROJECT_CONTEXT.md

## D003 — Log-Level Event Decoding for DeFi Action Classification

**Date:** 2026-10-02

**Decision:**
Do not infer financial actions (borrow, repay, supply, liquidate) from asset transfer events or contract interactions alone. Require receipt-level log inspection (`topics[0]` Keccak-256 event signatures) and participant matching against official protocol ABIs (starting with Aave V3 Pool).

**Reason:**
A transfer to a lending pool address can represent a deposit, a debt repayment, or a flash loan return. Classifying actions without event log evidence is methodologically indefensible.

**Implication:**
Lending transactions are deduplicated by hash, receipts are retrieved on-demand via the RPC layer, and unmapped/unsupported logs are classified as `unknown` or ignored if irrelevant (e.g., standard ERC-20 transfers).