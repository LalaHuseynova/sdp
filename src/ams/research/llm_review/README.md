# Blinded LLM reviewer

> Status note — 7 November 2026: This README documents the initial automated-review interfaces and versions. Later follow-ups cover the eight development groups; the current project overview records 6,325 assessed records in 256 inputs. AI proposals remain unverified and cannot replace genuine human reviews. See the [current research guide](../README.md) and [project README](../../../../README.md).

This is an explicitly automated annotation assistant. It never writes human
review forms, invents independent reviewers, turns case labels into memory labels,
updates source trust, generates a final pilot or runs a defense benchmark.

```sh
.venv/bin/python scripts/review_mpbench_llm.py prepare --out research_data/my_new_llm_review
.venv/bin/python scripts/review_mpbench_llm.py check --plan research_data/my_new_llm_review
```

Those commands block sockets and cost zero. `prepare` currently supports the
preselected first 32-case development bag only. It freezes model, system prompt,
allowlisted inputs, 32 request IDs, exact input/version hashes, prices and the
existing USD 30 session. No hidden labels, warning hints, method outcomes or
future audits are rendered in model input.

The separate **paid** command, only after advance cost disclosure, is:

```sh
.venv/bin/python scripts/review_mpbench_llm.py run --plan research_data/my_new_llm_review
```

One physical attempt per ID, 12,288 maximum output tokens, official OpenRouter
GPT-4o-mini only. The existing BudgetGuard reserves full context before dispatch;
all arms, controls, judges and this review share the same parent allowance. The
32-job reservation sum is USD 0.8503296 at the frozen maximum rates. A free
credential-safe provider check precedes dispatch. API credentials are not saved.
No higher-rate fallback, hidden SDK retry or unverified-billing override is used.

`AnnotationSession` is a restricted extension over the existing durable accounting
session. It refuses inherited experiment arming/completion methods and accepts
only the immutable review jobs. Native replies are saved before billing validation.
Ambiguous dispatch outcomes halt all new calls. Completed replies are reused on
restart; an existing result version is checked and returned without another call.
MockTransport tests never contact a real endpoint and never claim actual spending.

Each reply proposes record/use safety, source-field origin and literal evidence,
plus independent criteria for question drafts. Mechanical validation checks all
IDs, exact quotes/roles, completeness and finish reasons. Offsets are computed
from source text, including repeated occurrences, rather than trusting generated
offsets. Semantic correctness and authorship remain unverified. No text/answer
correction is silently invented to make a reply pass.

`automated_proposals.jsonl` stores accepted proposals with explicit automated,
non-gold/non-human metadata. `review_failures.json` records rejected packets.
`responses/` and the shared private dispatch journal preserve actual replies,
native usage/finish reasons and receipts. `summary.json` reports label counts,
coverage and costs; its accuracy and defense-ASR fields remain `not_measured`.

Use the separate exploratory protocol in
`reports/LLM_EXPLORATORY_PROTOCOL_20261031.md` before designing an AI-feedback pilot.
The original human-validated protocol and genuine review imports remain unchanged.

## Second development version

The first paid bundle-level pass is preserved, including its failed complete-
packet validation. A separately disclosed second version uses at most eight
records per request and short, deterministic record/source/evidence references:

```sh
.venv/bin/python scripts/review_mpbench_llm_batches.py prepare --parent research_data/llm_review_dev_v2_20261031 --out research_data/my_new_batch_review
.venv/bin/python scripts/review_mpbench_llm_batches.py check --plan research_data/my_new_batch_review
```

Its separate paid `run --plan ...` command requires prior cost disclosure. For
the same first development bag it has 114 requests, 790 records and 48 question
candidates, with a USD 3.0292992 maximum-rate reservation sum. It reuses the same
USD 30 parent guard, rather than adding that amount to the allowance.

Reference expansion is mechanical. Source role and exact text are checked;
semantic correctness and author identity remain unverified. Partial batches do
not become complete source bundles. `automated_bundles.json` distinguishes
complete automated record coverage from incomplete input contributions. All
results remain automated proposals and cannot satisfy a human-review import.
Previous failures and charges are not erased or reported as independent votes.
