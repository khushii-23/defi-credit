
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

```text
docs/PROJECT_CONTEXT.md