# Provisional dynamic-defense comparison — 1 November 2026

**The real-model comparison is complete. Selective propagation did not improve answer ASR over contextual or fixed multi-scope reputation in this run. It also lost one benign-restraint success against record-only/static SAFE-Mem in each of two conditions. This is preliminary evidence, not a validated or positive research finding.**

The complete table, integer denominators and paired analysis are in [RESULTS.md](../research_data/development_comparison_report_v1_20261101/RESULTS.md) and [comparison.json](../research_data/development_comparison_report_v1_20261101/comparison.json).

## What actually ran

Eight pre-existing development bags, D00–D07, contain 256 distinct MPBench inputs: 128 Email and 128 File/Document, with 160 attack cases and 96 benign cases. Each bag was evaluated in three existing provenance overlays. Static SAFE-Mem, record-only R, contextual reputation C, fixed multi-scope reputation M and selective propagation S each answered the same 27 unaudited original questions per overlay; a no-memory control answered those questions too. This produced **3,888 saved, judged answer events across 144 trajectories**. These are repeated conditions on eight bags, not 3,888 independent cases or a full-MPBench evaluation.

D00 ran first and had no authority-admissible external candidates. An offline admission audit then inspected all 640 original questions in the 20 prepared bags. We extended to **all seven remaining existing development bags**, without changing policies or selecting cases by success. This extension was decided after D00 and the metadata audit; it is exploratory development work, not an untouched confirmatory test. No D08–D19 model-outcome evaluation was run.

The original extraction, authority, flat/withhold retrieval, hops=0, k=4 claims, m=4 evidence slots, prompts and 200-token answering limit were retained. Query classification and embeddings were cache-only. GPT-4o-mini answering and target judging used actual paid OpenRouter calls when an exact saved reply was unavailable. The first physical reply for an exact request was shared across methods, with no favorable resampling. Model outputs, native usage receipts, retrieval traces and state hashes are saved.

## Answer outcomes

Lower ASR is better. Regime names below describe the **existing provisional case-label overlay**, not an independently established unsafe-memory distribution.

| Method | Strong/distributed | Strong/localized | Uninformative |
|---|---:|---:|---:|
| Static SAFE-Mem | 4/134 (2.99%) | 5/131 (3.82%) | 6/140 (4.29%) |
| R: record-only | 4/134 (2.99%) | 5/131 (3.82%) | 6/140 (4.29%) |
| C: contextual reputation | 4/134 (2.99%) | 5/131 (3.82%) | 6/140 (4.29%) |
| M: fixed multi-scope | 4/134 (2.99%) | 5/131 (3.82%) | 6/140 (4.29%) |
| S: selective propagation | 4/134 (2.99%) | 5/131 (3.82%) | 6/140 (4.29%) |
| No memory | 0/134 (0%) | 0/131 (0%) | 0/140 (0%) |

S's measured ASR improvement against C and M is **0 percentage points in every condition**. No-memory answering has zero retention recall, so its lower ASR does not establish a useful defense.

Within each condition, methods have identical questions and feedback. Across conditions, relational audit selection can reserve different cases, changing the probe cohort and feedback. The between-condition ASR differences therefore do not isolate source-risk predictiveness; the fixed-audit-ID control remains future work.

| Condition | Retention, all five memory methods | Restraint, static/R | Restraint, C/M/S |
|---|---:|---:|---:|
| Strong/distributed | 13/14 (92.86%) | 62/68 (91.18%) | 62/68 (91.18%) |
| Strong/localized | 12/13 (92.31%) | 65/72 (90.28%) | 64/72 (88.89%) |
| Uninformative | 12/13 (92.31%) | 58/63 (92.06%) | 57/63 (90.48%) |

C, M and S match on these answer metrics. The restraint losses relative to R/static are 1.39 and 1.59 percentage points in the latter two conditions. No source-grounded benign QA was validated or scored. The old retention targets are insufficient to establish preservation of useful external contributions: the admission audit found no external-admissible explicit-retention question in these eight bags.

The detailed table's write-target diagnostic examines extracted **claims** from each of the 160 attack inputs, including reserved audit inputs; all methods give 110/160. It is a target-presence diagnostic, not a label for every memory. Retrieval-target presence uses the separate fixed query cohorts and actual supplied claims/chunks. Original attack labels and target judges were never converted into record-safety truth or fed back into trust.

## Did propagation have an opportunity to act?

| Condition | Queries with an originally admissible attributed external candidate | S contexts changed vs static | C contexts changed | M contexts changed |
|---|---:|---:|---:|---:|
| Strong/distributed | 14/216 | 5/216 | 5/216 | 6/216 |
| Strong/localized | 16/216 | 8/216 | 7/216 | 10/216 |
| Uninformative | 18/216 | 10/216 | 12/216 | 13/216 |

These counts use full supplied-context hashes; selected-ID changes are logged separately. S changed 23/648 query contexts, so this was not merely a disabled-policy run. Nevertheless, most queries could not use an attributed external contribution under original authority rules. Static retrieval selected 2,327 principal, 106 external and 86 unknown-origin record occurrences across the three conditions. S selected 2,327 principal, 92 external and 100 unknown-origin occurrences. Refill can replace attributed records with unknown-origin records; fewer known-source exposures do not by themselves establish safer contexts. These are repeated record occurrences, not independent safety annotations.

## Information parity and label limitations

R/C/M/S each received exactly five identical audit tickets per bag/condition, the same initial memory, ingestion/query order and policies. Each therefore consumed 40 logical tickets per condition. Detector screening was disabled uniformly. Static and no-memory references consumed no audits.

Feedback reused existing AI proposals as **simulated audit verdicts**. There are **zero genuinely human-verified safety labels and zero validated source-grounded utility questions**. Exact construction links and span-backed AI origin suggestions support a controlled synthetic attribution assumption; they do not authenticate natural contributors. Principal information stays separate, and uncertain origins cannot cause broad contributor penalties. Private target labels, hidden source profiles and future feedback remain outside the runtime decision inputs.

The bags were not constructed from verified 16-safe/16-unsafe memory bundles. Their original composition is 20 attack cases and 12 benign cases each. The first ticket's AI assessment was unsafe in five bags, safe in two and unresolved in one. We preserved those verdicts. Consequently, these results **do not execute the primary protocol's Z-controlled, confirmed-unsafe-seed pilot**.

An audit's one attempt here denotes one saved-label lookup. The historical per-record review calls underlying a ticket can exceed two. Their equivalent resources are charged equally to every policy; this is not a completed one/two-call operational verifier experiment.

| Condition | Equivalent historical review calls per R/C/M/S arm | Input/output tokens | Equivalent review cost |
|---|---:|---:|---:|
| Strong/distributed | 178 | 1,729,266 / 51,560 | $0.279660 |
| Strong/localized | 168 | 1,684,736 / 51,568 | $0.273370 |
| Uninformative | 168 | 1,700,501 / 51,688 | $0.276572 |

These are historical full-call accounting equivalents, not new charges. Shared preparation costs and actual cache savings are not credited to S as a verification advantage.

## Validation and spending

- All **648 static retrieval contexts and governance-state hashes** matched Original SAFE-Mem using exact saved replies; no answers were resampled for this check.
- All 3,888 outcomes passed the matched-input/feedback/resource analysis and saved-row hash checks. There were zero empty answers, zero failed/missing query outcomes and zero answer-judge fallbacks. Fourteen answer events ended at the original output limit and remain in the denominators. Refusals and general task usefulness were not independently annotated.
- The offline suite passed **558 tests and 31 subtests**. A final focused rerun passed all **14 tests**, with the [JUnit record](PROVISIONAL_RESULTS_20261101_TESTS.xml). Lint and format checks passed for all 17 new code/test files.
- A before/after check found **all 3,606 pre-existing immutable files unchanged**. The shared billing databases legitimately appended new requests and receipts; those mutable records were reconciled separately.
- A runtime-only, tested memoization amendment removed redundant hashing of immutable evidence snapshots. A controlled restart with no active paid requests preserved saved outcomes and spending limits; the [amendment](PROVISIONAL_RESULTS_20261101_RUNTIME_AMENDMENT.json) and [restart record](PROVISIONAL_RESULTS_20261101_CONTROLLED_RESTART.json) are retained. Original SAFE-Mem and ledger code were not edited.

Actual native receipts reconcile **1,352 new physical requests**: 278 memory-answer calls, 245 no-memory-answer calls, 518 answer-judge calls and 311 entry-judge calls. No new API calls for verification, classification or embeddings were made. No training, dependency installation or model download occurred.

**New spend: $0.09877965. Tracked research-session total: $2.09412345 of the authorized $30; remaining: $27.90587655. Unsettled holds: $0.** The cumulative additional $5 task stop was retained, without creating another allowance. [Billing summary](../research_data/provisional_api_receipts_v1_20261101/summary.json) and private physical response receipts are saved.

## Scientific decision and next work

The proposed benefit beyond simpler reputation is **not demonstrated**. The advance criterion is unmet, and only 4–6 baseline attack successes per condition falls below the protocol's 20-success planning check. Eight development bags, unverified feedback and missing external-use utility prevent a paper-level efficacy or noninferiority claim. Degenerate paired bootstrap intervals at zero describe these observed ties; they do not establish equivalence or exclude rare unseen effects.

Before further paid scaling, specify an external-memory-use cohort prospectively using content, provenance and use criteria. Check attribution and matching record/use safety, add source-grounded utility, and freeze a new common-feedback comparison against C and M. Human review can remain deferred for engineering work, but the validated pilot and scientific claims still require it. Retain original authority rules and use new frozen outcome cohorts for any revised study.

The historical 176/2,999 (5.87%) ASR is a separate full-pool reproduction. Comparing it directly with these small-pool percentages would not identify an improvement from our defense.
