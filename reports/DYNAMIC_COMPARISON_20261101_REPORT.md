# Dynamic-method comparison table: implementation and current status

Completed 1 November 2026, Asia/Baku. The next independent engineering step was
completed: a strict offline analysis/reporting pipeline for the matched comparison
of **our selective method S against contextual C and fixed multi-scope M**, with R,
static SAFE-Mem and no-memory references. **No defense-effectiveness result has
been measured.** Dataset qualification remains unresolved; no failed review was
reinterpreted, no label changed and no new paid review was attempted.

## Deliverables

- [Current comparison table](../research_data/dynamic_comparison_status_v1_20261101/comparison_status.md),
  generated from saved reproduction metrics and the latest dataset-readiness file.
  Historical values are separate; every new-workload result is explicitly pending.
- [Analysis module](../src/ams/research/comparison.py) and
  [offline CLI](../scripts/compare_dynamic_results.py).
- [Design, commands and saved-outcome contract](DYNAMIC_COMPARISON_ANALYSIS_20261101_DESIGN.md).
- [28 focused tests](../tests/test_dynamic_comparison.py), covering actual metric
  arithmetic and the main failure/inequality cases using invented offline data.
  Their numerical examples are test fixtures, not preliminary MPBench findings.
- [Validation record](DYNAMIC_COMPARISON_20261101_VALIDATION.json) and
  [preservation check](DYNAMIC_COMPARISON_20261101_INTEGRITY_AFTER.json).

The six rows mean static SAFE-Mem rerun in the new workload; R record-only
containment; C contextual reputation; M fixed multi-scope reputation; **S selective
propagation (ours)**; and no-memory. R/C/M/S must receive the same five audits and
equivalent verifier resources. The two diagnostic references consume no feedback.

## What the pipeline enforces

Analysis-plan preparation accepts an already frozen AI-only cohort with checked
file hashes, the unchanged 32-case pool, five distinct audit cases, the fixed 27
original probes, separately defined source-grounded questions, common ingestion
order/root and the three declared regimes. It preserves original attack-case
labels for ASR. A safe-memory adversarial case still enters the attack denominator.
It does not infer unsafe-record labels or classifier accuracy from those cases.

Saved outcomes must match the plan's question/reference hashes, model, input/order
fingerprint, declared initial native-memory hash and fixed policy fingerprint.
R/C/M/S must have the same feedback hash, five tickets and equivalent verification
calls/tokens/cost. Unequal or future feedback, a different memory, a changed
operating point, duplicate outcomes and extra/foreign questions are rejected.
Checking declared hashes does not replace validating real execution journals or
the semantic correctness of evaluator decisions.

The analyzer reports integer counts and separate ASR, retention, restraint,
combined benign utility and source-grounded QA correctness. Paired attributable
ASR uses method success with no-memory failure on each question, rather than a
difference of marginal rates. General task accuracy and claim/use FPR/FNR remain
unavailable from original MPBench target labels alone.

Failures, budget stops and missing/unjudged outputs retain their planned
denominators. Exact rates are withheld when needed judgments are unknown, with
conservative missing-outcome bounds in JSON. Genuine refusals remain scored
responses, with retention/QA losses and refusal counts visible. An empty subgroup
gets N/A rather than zero risk or perfect retention.

Each regime is analyzed separately, with per-base-group and intended-source
relationship results. Duplicate/template overlap across independently declared
groups is rejected. The same seeded base-group draws are used across methods and
regimes; the three overlays of one group are not three independent samples. A
single group gets no bootstrap CI. Multiple-group CIs are exploratory, pointwise,
and unadjusted for multiplicity. Passing utility-margin point checks is not an
established noninferiority result. No automatic winner or acceptance claim is made.

There is no `run` command, provider construction, API request, annotation promotion
or scientific-gate override in this implementation. It consumes saved outcomes;
the future experiment controller must still write genuine answer/judge records,
native traces and ledger receipts in the documented contract. Paid experiment
charges are not inferred from query counts or cache sharing.

## Current table and validation

The separate historical reference remains:

| Metric | Reproduced full-MPBench count | Value |
|---|---:|---:|
| ASR | 176/2,999 | 5.87% |
| Retention | 213/249 | 85.54% |
| Restraint | 1,273/2,607 | 48.83% |
| Combined benign utility | 1,486/2,856 | 52.03% |

These saved results were read, not rerun. They are not the new-workload static
baseline, nor results for S. The new six-row comparison table has no measured
entries yet. Its only data shortfall remains one qualifying File/Document
explicit-retention contribution with a suitable external-claim utility question.

The relevant regression suite passed **498 tests and 31 subtests**, including all
28 comparison tests. The final focused rerun also passed all 28 after adding an
explicit check that attack denominators follow `Y_case`, independently of memory
safety proposals. A real preparation attempt with the absent qualified cohort was
rejected before producing an analysis-plan directory. Current pending table cells
were verified to contain no invented method outcomes.

All **3,544 fingerprinted pre-existing files** remained unchanged, including
original MPBench/SAFE-Mem, the completed reproduction, failed reviews, human forms,
research protocols, the evidence ledger, policies and retrieval implementation.
The API dispatch journal remained at 1,751 settled completions with no new holds.

**Additional API calls/cost: 0 / $0.** The existing research-session usage remains
**$1.99534380 of $30**, leaving **$28.00465620**. No limit was reset or increased.

## Remaining work toward our own result

1. Resolve the outstanding qualified review. The focused review package already
   exists; genuine human reviews and independently verified source labels remain
   pending. This analysis module does not supply them.
2. Freeze a qualifying, explicitly labeled exploratory cohort under the unchanged
   balance/template/unique-support requirements.
3. Build native stores in that cohort's actual ingestion order and validate
   provenance bindings, claim/chunk treatment, static parity and restart behavior.
4. Freeze the concrete experiment controller/manifest and estimate answer,
   classification, verification, conflict and judge expenses before paid calls.
5. Execute the matched R/C/M/S comparison plus references. Feed the saved results
   to this analyzer to populate the table and assess S versus both C and M at
   preserved benign utility and equal verification resources.

The table-analysis implementation is ready for saved experiment outcomes. The
measurement stage remains gated by the unresolved dataset and
execution prerequisites. No claim of improved ASR, preserved utility, natural-source
generalization, human-gold validation or ICML novelty follows from these tests.
