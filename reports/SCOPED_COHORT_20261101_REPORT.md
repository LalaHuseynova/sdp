# Scoped review to cohort and comparison handoff

Prepared 1 November 2026. **Engineering completed offline; no new real cohort,
defense evaluation, training, model download or API call. New API cost: $0.**

## Completed

Added [scoped_cohort.py](../src/ams/research/scoped_cohort.py),
[prepare_scoped_cohort.py](../scripts/prepare_scoped_cohort.py) and
[nine validation tests](../tests/test_scoped_cohort.py). The
[usage guide](SCOPED_COHORT_20261101_GUIDE.md) describes the actual post-review
commands and remaining execution work.

The new freeze path requires an accepted, version-bound scoped question review
and a complete selection from the existing selector. It preserves every original
AI source vote, checks actual record/packet/artifact hashes, and refuses changed
votes, stale reviews, incomplete selections and overwrites. It reuses the existing
slot/event constructor rather than introducing a different sampling method.

The resulting schema records human-reviewed questions separately from AI-assessed
source safety. It retains all 16 selected questions, even when a question's source
is reserved for audit in an overlay. A question review never becomes a human
source-safety label, another incident vote, live trust evidence or permission.
The software validates coordinator-attested review records; it cannot itself
authenticate human identity or independence.

The analysis-plan adapter preserves that provenance while using the existing
comparison analyzer. It pins the R/C/M/S policies, common input/feedback hashes,
five logical audit tickets, original task categories and new utility-reference
hashes. Actual equivalent verification costs and saved model/judge outcomes are
still required for evaluation. No execution path is enabled by these tools.

## Validation and real-data status

- **528 tests and 31 subtests passed**, in 53.50 seconds. This includes all nine
  new tests and existing preparation, recovery, ledger, retrieval, sequential,
  planning, execution, native-store, review, comparison and budget tests.
- Positive freeze/analysis tests used explicitly invented temporary review
  declarations and fake balanced inputs. They are software tests, not human
  validation or MPBench performance results.
- Negative checks cover pending reviews, modified source votes, altered QA
  decisions/selection, changed memory text, source-label promotion, lost human-QA
  metadata and stale analysis-plan dependencies.
- The real current workflow has **0 first passes, 0 second passes and 0
  adjudications**. Its reference is unreleased, with **0 accepted human-QA
  candidates and 0 human-verified memory labels**.
- Running the new freeze against the real pending readiness refused with:
  `Complete selection and an accepted scoped QA review are required before freezing`.
  No cohort output directory was created.
- CLI help exposes only `freeze`, `verify` and `analysis-plan`; all commands run
  inside the existing offline network guard.

Existing AI assessments remain 65 safe-for-use, 104 unsafe and 87 uncertain source
bundles across the 256 reviewed development inputs. These are AI assessments,
not independently verified labels or measured annotation accuracy. The actual
selection still lacks one qualifying File/Document explicit-benign source-grounded
question. Every other planned stratum has sufficient group-disjoint capacity in
the current readiness report. No label, quota, frozen question or earlier failed
review was changed to manufacture eligibility.

## What is still pending

The actual reviewers must complete the pending question review. If accepted, rerun
readiness, freeze the exploratory cohort and prepare its analysis plan using the
new guide. A rejection or unresolved decision keeps the current selection blocked.

The source-safety basis will still be AI-only. The resulting one development
group, with three paired overlays, cannot be called the protocol's human-validated
locked pilot or three independent groups. Human source-safety validation and a
new held-out confirmation study remain separate requirements for stronger claims.

Before any model experiment, construct/validate native memory in the selected
ingestion order, verify trusted source bindings and prepare a versioned, costed
execution manifest. Then run matched static SAFE-Mem, R/C/M/S and diagnostic
references, privately judge actual saved answers and report safety together with
retention, restraint, source-grounded utility and verification expense. The
current new-method comparison table remains pending. Historical 5.87% ASR belongs
to the completed original reproduction and is not a new-method result.

The research-session ledger remains **$1.99534380 used**, **$0 held** and
**$28.00465620 remaining** under the existing $30 limit. All 1,751 existing
dispatches are completed; no new dispatch was added. No execution cost is
estimated or committed by this engineering handoff.

## Integrity

The before/after fingerprint check covers 3,579 pre-existing source, configuration,
dataset, research-output, report and test files. Results are saved separately in
the accompanying integrity and validation JSON files. This step adds versioned
files and preserves the original data, SAFE-Mem, protocol, existing outputs and
review workflow.
