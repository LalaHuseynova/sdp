# Cost, token, and failure accounting

This document defines the accounting procedure for the full Original SAFE-Mem reproduction. The procedure was reviewed while the evaluation ran; the final accounting section below was added after successful completion on 2026-10-28.

The approved scope is Original SAFE-Mem with GPT-4o-mini, the complete 6,240-record MPBench memory pool, all applicable evaluation cases, an estimated software stop at $27, and a $30 spending maximum with a $3 margin. The existing key has a separate $200 provider limit. That provider limit does not enforce this experiment's $30 maximum. Local reservations, provider price ceilings, and monitoring implement the experiment's spending control; they are not an unconditional account-billing guarantee.

## Files included in experiment-wide accounting

All three execution roots share one persistent budget database and one response cache. Aggregate their costs once across the entire sequence; resuming the pipeline does not reset the allowance.

| Execution root under `results/full_mpbench_reproduction/` | Role | Accounting treatment |
|---|---|---|
| `6f4b102be735` | Initial billing preflight rejected with HTTP 400 because a plugin-disable entry had an incompatible schema. No benchmark job started. | Its preflight usage ledger is empty and it has no settled charge. Preserve its $0.01926 `BadRequestError` hold in the shared database. The stored key-usage readings show no observed change across this attempt, but that is not grounds to erase a hold. |
| `e392f927caac` | Original full run, interrupted during concurrent memory prefetch after the billing guard halted. | Include its uncached completed-response usage and its live preflight response. Include all its settled and unresolved reservations through the shared database. Its incomplete benchmark outputs do not constitute final evaluation scores. |
| `e0b7ceead3a6` | Resumed original pipeline after explicit accounting review and optional estimated-usage handling. | Include newly uncached responses. Its preflight and many memory calls replay prior cache entries and incur no new API charge. Use its completed benchmark outputs only after full-result validation. |

Primary accounting files:

- `reports/safemem_full_mpbench/safemem_only_request_budget.sqlite`
- Each root's `billing_preflight_usage.jsonl`
- Each root's nested `usage.jsonl`
- Each root's `execution.json` and job `budget_progress.json`
- `reports/safemem_full_mpbench/accounting_repair_review.json`
- Stored provider status/reconciliation snapshots, including `provider_reconciliation_progress.jsonl`

The initial generic billing halt was reviewed without releasing funds. The review changed 13 dead pending reservations to unknown and cleared only the reviewed `unverified_billing` halt. Before and after the review, reported settled charges were $1.3298868 and retained holds were $0.2937. The 15 old unknown reservations consist of one rejected preflight, 13 interrupted attempts, and one opaque old `unverified_billing` record. The old adapter did not preserve enough receipt detail to prove the final record's exact cause. Do not relabel it as a verified successful response or a confirmed missing-cost response.

## Field meanings and provenance

| Source and field | Meaning | Aggregation rule |
|---|---|---|
| Budget `reservations.reservation_id` | One authorization of a possible SDK HTTP attempt, created before SDK dispatch. Strict mode disables hidden SDK retries. | Count each reservation once. An authorization alone does not prove that the provider received the request; interruption or connection failure can occur before receipt. |
| `state='settled'`, `actual_nanodollars` | Finite, nonnegative OpenRouter `usage.cost` from a valid approved-model completion, rounded upward to the next nanodollar for accounting. | Sum once for reported charges. Never replace it with a token-price estimate. |
| `state='breach'`, `actual_nanodollars` | A reported charge exceeded its reservation, or authoritative settlements conflicted. The guard records the amount and halts. | Include in reported charges and prominently report the breach. A final successful run should have no breaches. |
| `state IN ('pending','unknown')`, `reserved_nanodollars` | Full conservative charge allowance still held for an unresolved attempt. | Sum separately from reported charges. Do not report it as actual spend, zero it, or release it because a run restarted. |
| Budget `metadata.generation_id` | Provider completion identifier, when a receipt preserved it. | Use for auditing and duplicate-ID detection. Do not silently deduplicate charged reservations solely by generation ID or cache key. |
| Budget `metadata.request_id` | SHA-256 of `ChatRequest.cache_key(provider)` in repaired unknown/error handling. It hashes the unchanged request configuration and messages. | Can identify the corresponding cache entry. It is not a wire request ID and is absent from older receipts and normal settled receipts. |
| Budget `metadata.input_tokens`, `output_tokens` | Native token counts supplied by the provider when known. | Sum known native counts; report missing-count records separately. Missing values are unknown, not observed zero. |
| Budget `metadata.usage_details.*_known` | Explicit count-availability flags on repaired receipts. | Treat absent counts as unknown even when the neutral `Usage` object contains zero. |
| `error_type='MissingBillingCost'`, `metadata.estimated_cost_usd` | A structurally valid approved-model response was accepted under the explicit estimated-usage option without authoritative `usage.cost`. Its full hold remains unknown. | Report its returned native-token price estimate separately from reported charges. If either native token count is absent, this estimate uses the full reservation ceiling. This is a usable response with uncertain billing, not a failed benchmark task. |
| Usage ledger `cached=false`, OpenRouter provider | A completed logical model call returned and was recorded after retry handling and cache insertion. | Sum its native tokens and returned `cost_usd` across all three roots, including separate preflight ledgers. This count excludes failed retry attempts. |
| Usage ledger `cached=true` | Reuse of a cached response. Its token and cost fields describe the stored response, not a new provider charge. | Count as a cache hit. Exclude both tokens and cost from newly paid usage. Cache reuse may be reported separately as logical workload. |
| Usage ledger `cost_usd` | Usually OpenRouter's reported `usage.cost`; in optional missing-cost mode, the adapter's conservative returned estimate. | It is a mixed field after the repair. The ledger has no explicit estimate flag or receipt ID; use the budget database to distinguish billing provenance at the aggregate level. |
| Usage ledger `provider='local'` | MiniLM embedding computation in this setup. Its token counts are local workload estimates and its API cost is zero. | Report separately from OpenRouter native paid tokens. |
| Key status `usage` / `byok_usage` | Cumulative usage across the shared key, including work outside these execution roots. Status may lag or reflect requests before their responses reach the client. | Use a baseline delta only as a reconciliation signal. Never label the whole key balance or its delta as proven experiment-only spend. |

`UsageLedger.record()` excludes cached responses from its in-memory usage totals but still writes their historical token and cost values to JSONL. A raw sum over every JSONL line would therefore double count replayed usage. `ManagedClient` records only final returned responses; retries and exceptions do not produce a completed-response ledger row. Cache keys are content based and the cache stores only one entry per key, while concurrent cache misses may make multiple paid calls for the same key. Counting unique cache entries consequently undercounts paid attempts.

The budget database currently records every paid operation as stage `chat`. It does not contain the ledger's `memory_write`, agent, or judge stage attribution. The existing usage JSONL schema contains no request ID, generation ID, or timestamp. A cost-matching or token-matching join between individual ledger rows and reservations is therefore not a reliable reconstruction method. Report ledger stage totals and budget billing-provenance totals separately, and explicitly show any aggregate reconciliation difference.

## Final aggregation procedure

1. Wait until the paid process has stopped. Preserve its exit status and full/incomplete evaluation status. Do not infer completion from the number of cached responses, prefetch progress, or authorization count.
2. Open the shared budget database with SQLite URI `mode=ro`, enable `PRAGMA query_only=ON`, and use one read transaction. Do not instantiate a writer, clear holds, truncate a WAL, or edit any reservation as part of reporting.
3. Read budget configuration, reservations, and review events in that same snapshot. Compute all money using integer nanodollars or `Decimal`, not repeated binary-float addition.
4. Compute reported charges `C` as the sum of `actual_nanodollars` for settled/breach rows, uncertainty `H` as the sum of full reserved amounts for pending/unknown rows, and conservative commitment `B = C + H`. Reconcile `C` and `H` with the stored budget totals. Report `$27 - B` as remaining local allowance. Explicitly show blocked state, breach count, and any remaining pending records.
5. Group unresolved records by `error_type`, retaining their counts and full holds. Separately total `MissingBillingCost` estimated returned costs and known native tokens. Unknown costs are not confirmed zero charges. Unknown-token records make token totals lower bounds.
6. Read complete newline-terminated JSONL records from every root's separate preflight ledger and nested usage ledgers, once per file. Report malformed/truncated lines rather than silently dropping them. Group OpenRouter rows by root, stage, and `cached`; group local embedding rows separately.
7. Sum only uncached OpenRouter rows for completed paid-response usage. Include the original uncached billing canary exactly once; exclude its later cached replay. Report cached logical workload and cache-hit counts separately. Keep provider-reported charge totals separate from returned mixed-cost ledger totals.
8. Reconcile native token and completed-response totals against budget metadata. A settled receipt can exist without a completed-response ledger row if interruption occurred between the receipt, cache write, and ledger write. Conversely, accepted missing-cost responses have unknown holds and estimated ledger cost. Disclose differences; do not discard one source to force agreement.
9. Use stored key snapshots, and any final read-only key snapshot collected by the main process, to compare against the initial preflight baseline. Explain key sharing, timing, and unknown holds as limits on attribution. Do not request or create a new key during final reporting.
10. Save machine-readable aggregates and a human-readable final cost table. Include all three roots, snapshot time, number of complete ledger records, native-token availability, estimate counts, uncertain holds, failure categories, and the exact paths used. Report cost separately from task success or attack metrics.

The first stored key baseline for this sequence is $24.215196455 before `6f4b102be735`. The stored resume baseline is $25.546356005. Their difference is $1.33115955, while reported charges before resumption were $1.3298868; the difference is $0.00127275. This is an observed key-wide discrepancy, not a verified assignment to any particular unknown attempt. The full $0.2937 old hold remained reserved.

## Failure categories

Report these categories separately rather than equating all unknown reservations with failed tasks:

- **Rejected request:** `BadRequestError`, such as the initial plugin-schema preflight. It returned no usable completion and has no verified charge in the ledger.
- **Usable response, unverified billing:** `MissingBillingCost`. The original output is retained and evaluation can proceed under the approved estimated policy; its full financial hold remains.
- **Incomplete provider response:** `IncompleteResponse`, including parsed HTTP 200 error payloads or empty choices. The same original request may retry, with a fresh reservation for each SDK attempt.
- **Transport/API uncertainty:** Timeout, connection, and other SDK exception types. A later successful retry does not erase an earlier financial hold.
- **Interrupted attempts:** `InterruptedAfterBillingStop` and any final pending records. Response receipt, provider execution, and charge status may be unknown.
- **Opaque legacy billing failure:** The old `unverified_billing` row. Its missing subtype is an explicit limitation.
- **Protected accounting violations:** Invalid/negative/nonfinite charges, BYOK billing, unexpected model, native-usage price-bound violation, settlement conflict, or cost above reservation. These persistently halt dispatch and require separate disclosure.

Valid model refusals and valid messages with empty content are preserved as original outputs. They are not retried merely to obtain a more useful answer. Whether such an output succeeds or fails a benchmark task is determined by the original evaluation logic, independently of transport or billing classifications.

The following final aggregates were added after the completion signal and full-output validation. Benchmark task metrics are reported separately from this cost accounting.

## Final accounting after successful completion

Snapshot: `2026-10-28T14:34:24.085863+00:00`. The active job exited with code 0 and status `full_validated` at `2026-10-28T14:29:59.198512+00:00`. Full output validation records 6,240 ingested memory cases, 2,999 attacks, and 2,997 benign evaluations. Machine-readable totals are in [final_cost_accounting.json](final_cost_accounting.json).

| Experiment-wide quantity | Final value |
|---|---:|
| Authorized possible HTTP attempts, all three roots | 37,941 |
| Settled provider receipts / completed uncached OpenRouter responses | 37,922 |
| Provider-reported charges | $3.9186663 |
| Full holds for 19 unresolved attempts | $0.371352 |
| Reported charges plus conservative unresolved holds | $4.2900183 |
| Remaining $27 software allowance | $22.7099817 |
| Pending / breaches / persistent block | 0 / 0 / False |
| Completed uncached OpenRouter native input tokens | 17,588,758 |
| Completed uncached OpenRouter native output tokens | 2,134,002 |
| Accepted responses with estimated missing billing cost | 0 |
| Excluded OpenRouter cache replays | 24,790 |
| Excluded cache replays, all providers | 100,693 |

All 37,922 uncached completed-response ledger records have provider-reported charges. The estimated-cost option was enabled for robustness but no `MissingBillingCost` response occurred. The sum of uncached ledger charges matches settled budget charges exactly, and ledger input/output token totals match settled receipt metadata exactly. No financial hold was released to force reconciliation. Tokens consumed by the 19 uncertain attempts remain unknown, so the completed-response native token totals are not a complete token bill for every authorization.

### Contributions by execution root

| Root | Authorizations | Settled receipts | Reported charges | Retained uncertainty |
|---|---:|---:|---:|---:|
| `6f4b102be735` | 1 | 0 | $0 | $0.01926 |
| `e392f927caac` | 7,997 | 7,983 | $1.3298868 | $0.27444 |
| `e0b7ceead3a6` | 29,943 | 29,939 | $2.5887795 | $0.077652 |

The resumed job alone has 29,939 uncached returned responses costing $2.58877950. This is not the total cost of the full reproduction: the earlier interrupted attempt and original live billing preflight contributed usable cached responses and remain included above.

### Uncached OpenRouter usage by stage, across all roots

| Stage | Completed responses | Native input tokens | Native output tokens | Reported charges |
|---|---:|---:|---:|---:|
| `agent_answer` | 7,784 | 3,804,776 | 266,881 | $0.73084500 |
| `billing_preflight` | 1 | 354 | 25 | $0.0000681 |
| `judge` | 13,433 | 4,918,388 | 363,390 | $0.95574360 |
| `memory_write` | 11,860 | 7,222,402 | 1,486,052 | $1.97499150 |
| `use_type` | 4,844 | 1,642,838 | 17,654 | $0.25701810 |

### Unresolved authorizations and retry uncertainty

| Error category | Authorizations | Full retained hold |
|---|---:|---:|
| `APITimeoutError` | 2 | $0.03906 |
| `BadRequestError` | 1 | $0.01926 |
| `IncompleteResponse` | 1 | $0.01932 |
| `InternalServerError` | 1 | $0.019272 |
| `InterruptedAfterBillingStop` | 13 | $0.2547 |
| `unverified_billing` | 1 | $0.01974 |

The resumed run added four uncertain attempts: two timeouts, one server error, and one structurally incomplete provider response. All four preserved request hashes have a corresponding successful chat completion in the final cache. The original request was retried under the same model, prompt, temperature, and token ceiling; each attempt received a fresh reservation. Those are transport/accounting incidents, not automatically failed benchmark outcomes. The older 15 uncertain records retain the same $0.2937 held before resumption. There are no pending records, breaches, or active accounting blocks.

### Cache and key-wide reconciliation

OpenRouter cached replay rows contain 14,312,308 historical input tokens, 2,722,087 historical output tokens, and $3.78009840 in historical response cost fields. None of these values is added to new paid usage. Local uncached embedding calls number 41,434, cost $0, and report 4,935,534 local workload tokens; these are excluded from paid native OpenRouter token totals. The cache is an inventory of unique request keys, not a count of billed requests.

The stored final key status, read at `2026-10-28T14:32:20.071409+00:00`, reports cumulative usage $28.135135505. Against the initial $24.215196455 baseline, its key-wide delta is $3.919939050, which is $0.001272750 above the experiment's settled receipts. This difference fits within the retained $0.371352 uncertainty. It is supporting evidence, not proof of exact experiment-only billing: the key can be shared and unresolved or delayed charges are not individually attributable. No key setting was changed for this report.

Every usage file was read once, all JSONL records were newline terminated and valid, and no malformed records were found. Budget row totals match stored configuration totals. The JSON preserves file paths and hashes, stage/root groups, native-token availability, review-event details, and exact monetary strings. No API call, account change, source change, cache edit, budget mutation, or hold release was performed for this aggregation.
