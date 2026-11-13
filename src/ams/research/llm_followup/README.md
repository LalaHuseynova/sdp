# Missing-item automated review

> Status note — 7 November 2026: This is one stage in the automated-review history. Later candidate, quality-control and comparison stages exist in `pilot_finish/`, `ai_pilot/` and `provisional_run/`. Saved failures and accepted proposals remain separate; no human validation is implied. See the [current research guide](../README.md) and [project README](../../../../README.md).

Follow up mechanically rejected development batches only, one item per request.
Previous accepted proposals, failed replies, human forms and primary protocols
are preserved. No earlier votes or failure text are included in model input.
All outputs remain AI proposals; this does not run a defense benchmark.

```sh
.venv/bin/python scripts/complete_llm_review.py prepare --parent research_data/llm_review_small_batches_v2_20261031 --out research_data/my_followup_version
.venv/bin/python scripts/complete_llm_review.py check --plan research_data/my_followup_version
```

Preparation/checking block sockets and cost zero. Only the explicit `run --plan`
command makes paid requests after the required advance cost disclosure. It uses
the same existing USD 30 session and durable response/billing journal. Unknown
outcomes stop dispatch. No hidden retries or replacement labels are generated.

```sh
.venv/bin/python scripts/complete_llm_review.py analyse --plan research_data/my_followup_version --out research_data/my_new_analysis
```

Analysis is offline and reports coverage, external claim-backed QA opportunities,
composition shortfalls and structural review flags. Eight hash-selected packets
are blinded for a future independent quality check. They are not completed human
reviews. Neither valid references nor complete coverage establishes semantic
accuracy, real authorship or defense efficacy. The result manifest protects the
merged view while original proposal versions remain individually attributable.
