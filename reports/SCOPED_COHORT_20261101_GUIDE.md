# Freeze a cohort after the scoped question review

Prepared 1 November 2026. The new tool is offline and does not run a defense,
answer questions, judge outputs, call an API or download a model. **The real input
is still pending: no genuine reviews have been submitted and no cohort was
created by this step.**

This closes the handoff between the [human review workflow](FOCUSED_REVIEW_WORKFLOW_20261101_GUIDE.md)
and the existing comparison analyzer. It preserves human approval of a particular
question separately from AI assessments of source safety. A reviewed question
does not make its source bundle, original MPBench task or surrounding memories
human-verified safe.

## 1. Finish the actual review and recheck readiness

Use the previous guide for the two independent first passes, reference release,
second passes, any genuine disagreement resolution and coordinator attestation.
Do not fill reviewer declarations on someone else's behalf. The software checks
declarations and evidence consistency; it cannot authenticate the people or their
independence. Negative and uncertain reviews remain valid outcomes.

After an accepted scoped QA import exists, generate a **new** readiness output:

```sh
.venv/bin/python scripts/manage_focused_review.py readiness \
  --workflow research_data/focused_review_workflow_v1_20261101 \
  --prepared research_data/mpbench_provisional_v1_20261029 \
  --reviews research_data/ai_pilot_post_adjudication_view_v1_20261101 \
  --accepted research_data/my_versioned_QA_import \
  --out research_data/my_scoped_QA_readiness
```

Acceptance of the question alone is insufficient: the unchanged selector must
also find a complete, group-disjoint selection. Do not force the File/Document
explicit-benign quota or replace a rejected question with an unvalidated answer.

## 2. Freeze the data when both checks pass

```sh
.venv/bin/python scripts/prepare_scoped_cohort.py freeze \
  --prepared research_data/mpbench_provisional_v1_20261029 \
  --readiness research_data/my_scoped_QA_readiness \
  --out research_data/my_scoped_cohort

.venv/bin/python scripts/prepare_scoped_cohort.py verify \
  --cohort research_data/my_scoped_cohort
```

The freeze refuses existing destinations, pending/rejected reviews, changed
memory versions, altered AI votes or changed selections. It verifies the actual
accepted receipt and its dependencies rather than trusting an edited readiness
flag. A pending real input is rejected before an output directory is created.

The unchanged constructor supplies 32 distinct inputs, the three initial regimes
(strong/localized, strong/distributed, uninformative), common ingestion order and
root, and five shared audit tickets per R/C/M/S policy. Each overlay reserves the
same five audit cases across arms and has 27 original probes, followed by its
unaudited safe-source utility questions. Source-safety balance is **16 AI-assessed
safe and 16 AI-assessed unsafe bundles**, with 16 cases per domain. Official input
case labels remain separate: 20 attack cases and 12 benign cases.

The old constructor's hardcoded zero-human-QA bookkeeping is confined to a
temporary staging directory. Its data are reused in a new schema with accurate
per-question review provenance; that temporary legacy manifest is not published.
The old constructor and its outputs are unchanged.

Important outputs:

- `manifest.json`: hashes, dependencies and execution disabled.
- `public/*.json`: runtime event streams without private labels or references.
- `private/selection.json`: selected inputs and source-label basis.
- `private/selected_questions.json`: all 16 selected utility questions, including
  those reserved for audit in a particular overlay.
- `private/annotation_provenance.json`: accepted question review scope, hashes,
  selected human-QA count, remaining AI-QA count and zero human source labels.
- `private/*.json` episode files: evaluator labels, scheduled AI audit verdicts
  and utility references. Never expose these to the defense or share them with
  blinded reviewers.

Human QA approval does not create another source incident or change a source vote.
The frozen audits remain explicitly AI-assessed and independently unverified.
This is an **AI-source-safety exploratory cohort**, not the human-validated pilot
specified by the original protocol. One development group and its three overlays
are not three independent groups or the planned locked pilot.

## 3. Prepare the evaluator's comparison plan

```sh
.venv/bin/python scripts/prepare_scoped_cohort.py analysis-plan \
  --cohort research_data/my_scoped_cohort \
  --case-index research_data/mpbench_provisional_v1_20261029/private/evaluator_case_index.jsonl \
  --group-id AI00 \
  --out research_data/my_scoped_analysis_plan
```

This creates `study.json`, `annotation_provenance.json` and a dependency manifest.
The study uses the existing saved-result analyzer with basis `AI_exploratory`.
The companion file retains the scoped human-QA approval instead of discarding it
or claiming human source-safety certification. Original ASR/retention/restraint
reference hashes come from the evaluator-only official case labels; utility
references come from the separately frozen source-grounded questions.

The plan pins R/C/M/S policies, common input and audit hashes, and five logical
audit tickets for each policy. Static SAFE-Mem and no-memory references are also
planned by the existing analyzer. Actual equivalent verifier tokens/costs and
saved answer/judge outcomes must still be recorded during a later matched run.
An empty result set is incomplete; it cannot produce a successful defense result.

## 4. What still follows

Build and validate a native memory store in the newly frozen ingestion order,
verify trusted claim/chunk/artifact bindings, then prepare a versioned execution
manifest with a concrete cost estimate under the existing $30 session cap. The
live controller remains gated; these commands do not activate it.

Only actual matched static/R/C/M/S answers and private judgments can fill the
comparison table. The historical 5.87% ASR is a separate reproduction reference.
It cannot establish the new selective method's benefit. Preserve the main test:
selective propagation versus contextual and fixed multi-scope reputation at equal
feedback and verification expense, with separate benign-utility checks. A later
human-validated, independently confirmed study remains necessary for stronger
claims.
