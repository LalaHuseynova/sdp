# Original SAFE-Mem: completed full MPBench reproduction

**Status: full dataset completed and validated, 28 October 2026.** This is the requested Original SAFE-Mem / GPT-4o-mini arm, run through OpenRouter. It is not a reproduction of every backbone or baseline in the paper. No proposed dynamic provenance defense or training was added.

## Results compared with the paper

| Metric | Exact reproduced count | Reproduced | Published GPT-4o-mini SAFE-Mem | Difference, percentage points |
|---|---:|---:|---:|---:|
| End-to-end attack success rate (ASR), lower is better | 176 / 2,999 | **5.87%** | 6.2% | −0.33 |
| Retention recall, higher is better | 213 / 249 | **85.54%** | 85.9% | −0.36 |
| Restraint, higher is better | 1,273 / 2,607 | **48.83%** | 50.6% | −1.77 |
| Combined benign utility / annotated benign memory-use accuracy | 1,486 / 2,856 | **52.03%** | Not reported in MPBench Table 1 | — |

Published values come from Table 1 of the [original paper](../../safe-mem_paper.pdf), also recorded in the [paper protocol audit](../MPBENCH_PAPER_PROTOCOL.md). The run is close to that row; restraint is 1.77 percentage points lower. The reproduced numbers are actual outcomes, not copied paper values.

ASR's original 2,000-resample query-clustered bootstrap, seed 0, gives **[5.0%, 6.7%]**; the paper's Table 8 interval is **[5.4%, 7.1%]**. The original runner's separately retained Wilson interval is **[5.08%, 6.77%]**. These methods are explicitly distinguished. The overlapping intervals do not establish exact equality or statistical equivalence.

- **ASR** counts answers endorsing or acting on the attack target under the original answer judge. It is an end-to-end attack metric, not detector false-negative rate.
- **Retention recall** counts correct use of explicitly warranted benign memory.
- **Restraint** counts suggestive benign cases where the answer avoids asserting the unwarranted user claim, using the original judge.
- **Combined benign utility** is the count of correct annotated benign outcomes divided by 2,856. It is weighted by the two groups' actual sizes, not their unweighted mean. The original summary calls this field `benign_accuracy`.

| Additional requested metric | Availability |
|---|---|
| General task-answer accuracy | **Not computable**: these MPBench labels evaluate memory assertion/use rather than complete task-answer correctness. |
| Classifier false-positive rate (FPR) | **Not computable**: complete safe/unsafe labels for all extracted or retrieved claims are unavailable. |
| Classifier false-negative rate (FNR) | **Not computable** for the same reason. ASR is not substituted for FNR. |

### Attack categories

| Official canonical category | Successful attacks / scored cases | ASR |
|---|---:|---:|
| Repetition | 39 / 600 | 6.50% |
| Explicit keyword | 41 / 599 | 6.84% |
| Delayed conditional | 33 / 599 | 5.51% |
| Fact injection | 41 / 601 | 6.82% |
| Experience injection | 22 / 600 | 3.67% |

Other original diagnostics are preserved in `mpbench_summary.json`: poison-written rate 58.82%, poison-retrieved rate 3.10%, no-memory attack base rate 0.13% (4/2,999), attributable ASR 5.87%, and the original conflict/elevation, foreign-memory, flag, and refusal diagnostics. A flag rate is not called classifier FPR. No lexical answer-judge fallback was detected in the completed outcomes.

## Full data and shared memory coverage

- **6,240 unique official source records were ingested into `pool0`**: 3,241 attack inputs and 2,999 benign inputs. This is one shared pool.
- All **244 write-only inputs** remain in memory construction. They have no readable evaluation question, so they are not scored query cases.
- Exactly **5,996 unique readable outcomes** completed: **2,999 attacks + 2,997 benign cases**.
- All 2,856 annotated benign cases were scored: 249 retention + 2,607 restraint. The other 141 readable benign cases were answered but lack target annotations and therefore do not enter the utility denominator.
- The original extractor produced **22,089 entries** and the graph records one store. There are 1,271 source inputs with no extracted entries; they remain recorded ingestions. The 6,240 figure describes source memory cases, not a forced count of extracted claims.
- **Zero required cases were skipped or left incomplete.** All primary answers and all 2,999 attack no-memory control answers are nonempty.
- Raw official files, labels, questions, ordering before the original shuffle, and canonical attack categories are unchanged. The tolerant original loader consumes all JSON objects, including the line containing two objects.

| Official file | SHA-256 |
|---|---|
| `adversarial_data.jsonl.jsonl` | `f2d23a5a2d483889eb2fdd9a2a082f0759603bc0a17664814a7caafbd318f90d` |
| `benign_data.jsonl.jsonl` | `707ef7e311e147d9818a8a9e04293296fc6bf3390241e4cac23c8145765b62d5` |

Official dataset repository revision: `6886880a7c29625e0109e0ad91d0e095029f1577`. The [dataset integrity record](../../results/full_mpbench_reproduction/e0b7ceead3a6/4omini/safe_mem/full_mpbench_4omini_safe_mem_pool6240-20261028T132726Z/dataset_integrity.json) and case catalog retain the complete validation evidence.

## Preserved experimental setup

Original upstream implementation revision: `bac6090985647d7aeff3b44da68e528607a89e0f`. The source configuration is `configs/v31_mpbench_withhold.yaml`; the frozen resolved configuration is [configs/4omini_safe_mem.yaml](configs/4omini_safe_mem.yaml).

- Memory extraction, agent answering, and judging: `openrouter:openai/gpt-4o-mini`. No model-family substitution or configured fallback.
- Local `all-MiniLM-L6-v2` embeddings; no paid embedding calls.
- Original typed `withhold` memory, sentence-level endorsement, five authority levels, provenance, authority/scope checks, conflicts, and original extraction/retrieval/security decisions.
- Maximum six extracted facts, `retrieve_k=4`, four evidence slots, zero evidence hops, external evidence disabled, seed 0, 16 workers, pool size 6,240, no `--limit` and no adaptive evaluation.
- Original prompt versions: `retention_sentence/v1`, `extract_typed_claims/v1`, `classify_use_type/v2`, `detect_conflict/v1`, `answer_typed/v2`, `judge_entry/v2`, `judge_answer/v1`.
- Original no-memory controls and judge decisions retained. The output label `no_defence` denotes the identity wrapper around typed SAFE-Mem; SAFE-Mem's internal security mechanisms remain active.

All **67 checked original memory, governance, baseline, prompt, and source-configuration files** match upstream. All **147 frozen source fingerprints** match the execution plan at final verification. Loader identity and transport/accounting instrumentation changes are listed below.

## Spending and interruptions

The user authorized a **$30 maximum** and a **$27 software stopping threshold**, using the existing key without configuring a new key or account limit. Before paid execution, the SAFE-Mem-only cold-cache estimate was **$4.40 typical / $16.51 conservative**. Those were planning estimates.

The persistent experiment-wide budget database now records:

| Budget item | USD |
|---|---:|
| Sum of authoritative OpenRouter charges for settled requests | **3.9186663** |
| Full conservative reservations retained for 19 unresolved attempts | **0.3713520** |
| Total accounted commitment | **4.2900183** |
| Software stopping threshold | 27.0000000 |
| Remaining below threshold after charges and holds | 22.7099817 |

Across all three execution attempts, there were **37,941 pre-dispatch authorizations**, **37,922 settled completed OpenRouter responses**, and 19 unresolved authorizations. Completed paid responses used **17,588,758 native input tokens + 2,134,002 output tokens**; unresolved attempts have unknown token counts and are excluded from those totals. There were also 24,790 OpenRouter cache replays, excluded from new paid usage.

There are **no pending requests, no accounting breach, and no active paid process**. This accounting includes the earlier interrupted attempts and does not add cached replay costs a second time. The unresolved amount is a conservative hold, not a claim that OpenRouter charged that amount. Every returned uncached completion in the resumed run had a provider-reported cost; the optional missing-cost estimate path was enabled but was not needed during that segment.

The [cost accounting report](COST_ACCOUNTING.md) and [final cost JSON](final_cost_accounting.json) give request authorizations, token totals, stage usage, cache exclusions, and failure categories. Run-directory usage by itself undercounts work paid before the interruption; use the shared budget and cross-attempt accounting for total cost.

Before each physical attempt, an atomic SQLite guard reserves 128,000 input tokens at the capped rate plus the requested output ceiling. It refuses dispatch when the request cannot fit below $27, including existing holds. Charges replace holds only when authoritative billing is available. Unknown requests keep their full reservation across restarts. Hidden SDK retries are disabled; managed retries each need another reservation. Invalid charges, BYOK billing, wrong models, or pricing breaches stop dispatch. Optional paid core plugins are explicitly disabled, with provider price caps and parameter-compatible routing.

This is conservative software monitoring scoped to this experiment, not an account-wide limit. No key/account limit was changed and no credits were purchased. Existing-key metadata was read with free GET requests for supporting reconciliation; key-wide usage may include unrelated shared-key activity and is not independently attributable to this run.

Two interruptions are retained in the logs:

1. The first billing preflight received HTTP 400 because disabled beta plugin entries still required additional schema. Those invalid entries were removed. The failed attempt's $0.01926 reservation remains held; it was not a scored case.
2. The initial full preparation attempt stopped automatically on an unverifiable billing receipt. The old adapter did not retain the subtype, so no precise cause is claimed. It had not produced final query scores. All unresolved and interrupted request holds were retained. After the optional estimated-monitoring path passed offline tests, a reviewed resume changed no financial totals or limits, replayed the original full lifecycle, and reused cached responses.

See [accounting_repair_review.json](accounting_repair_review.json), [interruption_audit.md](interruption_audit.md), and the complete console history. Initial execution passed 82 offline tests; the accounting repair passed 59 offline tests, including a concurrent reserve test stopping at $26.998272 before further HTTP. These test counts overlap and should not be added as unique tests.

## Methodological differences and limits

1. **OpenRouter transport and current provider/model alias.** All roles use the same GPT-4o-mini family as the published row, but the authors' exact backend revision is not pinned by the current alias. Backend routing, model revision, stochastic responses, and concurrent scheduling can affect outcomes. These are plausible contributors to differences, not experimentally isolated explanations.
2. **Collision-safe internal IDs.** The official files share 300 raw IDs across splits. Internal `adversarial:<raw_id>` / `benign:<raw_id>` identifiers prevent overwriting bookkeeping. Raw records, IDs, labels, prompts, and questions are preserved; split labels are not added to model prompts.
3. **Transport and accounting controls.** Provider rate ceilings, disabled optional plugins, explicit retries, persistent budget reservations, cache reuse, and progress journals are necessary execution instrumentation. Original prompts, generation ceilings, evaluation decisions, and memory algorithms are unchanged.
4. **Paper/release discrepancy.** The official files contain 2,891 distinct exact scored attack questions, whereas Appendix J says 2,893. All 2,999 released scored attacks are retained; the data was not edited to force the paper count.
5. **Requested scope.** This run covers the Original SAFE-Mem GPT-4o-mini MPBench arm only. Other backbones, other baselines, LoCoMo, and MINJA are not claimed as newly reproduced here. Earlier smoke results are excluded.
6. **Original output limits and concurrency.** At least twenty-two saved with-memory answers match cached responses that finished at the original 200-token limit; these outputs were scored without extending the limit or rewriting answers. For the 23 saved-answer/cache-winner discrepancies below (15 with-memory answers and 8 no-memory controls), the original response finish reason is unavailable in the saved outcome record, so the cache-based finish distribution is not a complete original-response distribution. The 2,991 matching no-memory control answers have cached normal finishes; the original finish reasons for the other eight controls remain unknown. Twenty-three saved responses (15 with-memory answers and 8 no-memory controls) differ from the final cache winner across 21 request keys. Concurrent duplicate cache misses can produce multiple responses before the original insert-first cache chooses one; this is a plausible explanation rather than an experimentally isolated cause. The saved outcome answers and judgments are the primary result record. Independent replay of all 14,216 original judge requests found no verdict mismatch or lexical fallback. A fresh pipeline replay from the final cache is not guaranteed to regenerate each original answer bit for bit; use the saved CSV for offline reanalysis. Affected case IDs and diagnostics are preserved in the independent audit.
7. **Unsupported metrics.** General task accuracy and detector FPR/FNR cannot be computed from the available ground truth. The 52.03% annotated benign memory-use result must not be compared with LoCoMo task accuracy.

## Saved artifacts and reproducible commands

The complete output directory is:

`results/full_mpbench_reproduction/e0b7ceead3a6/4omini/safe_mem/full_mpbench_4omini_safe_mem_pool6240-20261028T132726Z`

It contains:

- [Original summary](../../results/full_mpbench_reproduction/e0b7ceead3a6/4omini/safe_mem/full_mpbench_4omini_safe_mem_pool6240-20261028T132726Z/mpbench_summary.json)
- [All predictions, answers, controls, retrieval records, and judgments](../../results/full_mpbench_reproduction/e0b7ceead3a6/4omini/safe_mem/full_mpbench_4omini_safe_mem_pool6240-20261028T132726Z/mpbench_outcomes.csv)
- [Completed manifest and resolved execution settings](../../results/full_mpbench_reproduction/e0b7ceead3a6/4omini/safe_mem/full_mpbench_4omini_safe_mem_pool6240-20261028T132726Z/manifest.json)
- `usage.jsonl`, `outcome_progress-no_defence.jsonl`, `written_memories-no_defence.jsonl`, `case_catalog.jsonl`, `dataset_integrity.json`, and `graph_stats.json`.

Supporting artifacts:

- [Machine-readable final results](final_results.json) and [metric CSV](metrics.csv).
- [Frozen experiment plan](plan.json), SHA-256 `e0b7ceead3a667d0f7848f6de53605d1d999233aeb9a40d3cb0d8e2159650f16`.
- [Launcher execution and full validation record](../../results/full_mpbench_reproduction/e0b7ceead3a6/execution.json).
- [Source integrity](final_source_integrity.json), [cost accounting](COST_ACCOUNTING.md), [budget database](safemem_only_request_budget.sqlite), [console history](execution_console.log), and `cache/responses.sqlite`.
- [Independent final audit](final_validation_audit.md).

The approved execution command was:

```bash
.venv/bin/python scripts/run_full_mpbench.py \
  --plan reports/safemem_full_mpbench/plan.json \
  --execute --approved-budget-usd 30 --stop-at-usd 27 \
  --approval-note 'User approved Original SAFE-Mem only on complete MPBench with existing key, maximum 30 USD and software stop 27 USD; no account cap required.' \
  >> reports/safemem_full_mpbench/execution_console.log 2>&1
```

The completed job is recorded as `full_validated`; rerunning this frozen launcher recognizes completed output. An interrupted run reconstructs the original memory lifecycle using the shared cache rather than skipping an assumed first-N prefix. Keep the budget database and cache together; neither should be reset to bypass accounting.

Recompute the offline analysis without paid calls:

```bash
.venv/bin/python scripts/analyse_mpbench_reproduction.py \
  --run 4omini safe_mem \
    results/full_mpbench_reproduction/e0b7ceead3a6/4omini/safe_mem/full_mpbench_4omini_safe_mem_pool6240-20261028T132726Z \
  --output-dir reports/safemem_full_mpbench/final_analysis
```

The generic analyzer also lists other published rows as pending; those rows are outside this approved run, not incomplete cases within this SAFE-Mem result. This report's table is the scope-specific comparison.
