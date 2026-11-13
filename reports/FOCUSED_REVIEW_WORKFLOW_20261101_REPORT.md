# Focused review workflow: implementation and pending state

Completed 1 November 2026, Asia/Baku. The next unblocked implementation is complete:
an offline two-pass review/import workflow for the remaining source-grounded
question. **No genuine review has been performed or imported.** The workflow has
zero sealed first passes, second passes and adjudications; references remain
withheld. Dataset readiness and the main experiment remain blocked.

## Deliverables

- [Reviewer 1 first-pass page](../research_data/focused_review_workflow_v1_20261101/forms/reviewer_1/first_pass.html)
  and [Reviewer 2 first-pass page](../research_data/focused_review_workflow_v1_20261101/forms/reviewer_2/first_pass.html).
  Both show the frozen question, actual claim and four original source artifacts,
  with blank answers, evidence, decisions, identities and unchecked attestations.
- [Step-by-step usage guide](FOCUSED_REVIEW_WORKFLOW_20261101_GUIDE.md).
- [Workflow implementation](../src/ams/research/focused_review.py),
  [local page renderer](../src/ams/research/focused_review_page.py) and
  [offline CLI](../scripts/manage_focused_review.py).
- [Current scoped readiness](../research_data/scoped_QA_readiness_pending_v1_20261101/review_readiness.json).
  It reuses the original selector and preserves all source-safety proposals.
- [21 new tests](../tests/test_focused_review.py), using invented declarations in
  temporary test directories, not actual human reviewers.

## Implemented boundaries

First passes are sealed as new hash-checked records. Identical resubmissions are
idempotent; changed sealed records and concurrent writers are refused. Reviewer
identifiers are normalized to reject trivial aliases of one identifier. The tool
cannot prove that different identifiers represent different people.

The proposed reference is released only after both independent first-pass
declarations are sealed. Second passes are bound to their original person,
candidate, packet, first-pass hash and reference release. Reviewer pages do not
display peer votes. A distinct adjudicator's page is available only after genuine
differences between the submitted decisions, and its resolution must cite the
particular sealed records. Negative or uncertain concordant reviews are preserved;
the workflow does not manufacture disagreement to obtain a favorable decision.

Positive admission requires the relevant human QA decisions, scoped external
provenance, exact source/claim evidence and first answers matching a frozen alias
with whitespace-only normalization. The initial answers cannot be rewritten after
seeing references. Units, case, negation and source punctuation are not repaired.
Human semantic judgment remains essential; literal evidence alone is not truth.

A coordinator must explicitly declare genuine human involvement, independent
people and first-pass blinding, tied to the exact sealed review hashes. The
coordinator template remains blank/false. The software validates these declarations
and consistency; it does not authenticate physical identity, attest honesty or
guarantee annotation correctness. Accepted outputs are explicitly scoped to
**one new descriptive question and its supporting claim**.

Human QA acceptance does not certify the original MPBench use, all 19 records in
the contribution, the contributor's other memories or the AI source-safety labels.
No safe/unsafe source observation, authority change, permission grant or live-trust
update is created. Two reviewers of one question are not two independent incidents.
The original R/C/M/S policies and five-audit experimental design are unchanged.

The readiness adapter preserves the parent AI proposals byte-for-byte, adds only
an accepted scoped QA decision when one actually exists, and reports human QA
counts separately from source-safety provenance. It never calls the result a
human-gold dataset. Its new `review_readiness.json` contract deliberately cannot
be passed directly to the legacy AI-only freeze that would erase mixed-QA
provenance. A subsequent cohort/manifest version must preserve that provenance;
this step does not generate final pilot groups or arm experiments.

## Checks and current results

The relevant full regression suite passed **519 tests and 31 subtests**, including
all 21 new workflow tests. Coverage includes hidden references, genuine-declaration
requirements, identities, stale/malformed/duplicate submissions, exact Unicode
spans, immutable seals, single-writer locking, adjudication, rejected/uncertain
outcomes, scoped admission and separate source-versus-question readiness counts.

The actual pending package was checked directly: its blank first-pass template
was refused as a completed review; premature reference release was refused; no
sealed review or second-pass page was created. The new readiness report still has
**zero human-validated questions and zero human-verified memory labels**, with the
same one-case File/Document explicit-retention utility shortfall. No source case,
label or question was substituted to fill it.

The local page uses inert text for source contents, no remote assets, no server
submission and a restrictive no-network content policy. JavaScript syntax,
Unicode-offset round trips and initialization against the actual first-pass data
were checked locally. The initialization harness was corrected to include static
form fields; no production change was needed for that correction. Native browser
visual inspection was unavailable because computer-use permission was not granted.
No real review was filled or downloaded by the assistant.

See [validation](FOCUSED_REVIEW_WORKFLOW_20261101_VALIDATION.json) and
[JavaScript validation](FOCUSED_REVIEW_WORKFLOW_20261101_JAVASCRIPT_VALIDATION.json).
All **3,556 fingerprinted pre-existing files** were preserved; the existing review
forms, failed model results, original MPBench/SAFE-Mem, research protocols and
comparison implementation are unchanged. See [integrity](FOCUSED_REVIEW_WORKFLOW_20261101_INTEGRITY_AFTER.json).

**New API calls/cost: 0 / $0.** The shared research session remains at 1,751 settled
dispatches and **$1.99534380 of $30**, with **$28.00465620** remaining and no holds.
No limit was reset or increased. No defense experiment, training, model download
or dependency installation occurred.

## Next action

Two actual independent people must complete the first-pass pages and then the
released reference checks. A coordinator can use the guide to seal and validate
their new files, obtain adjudication only where needed, and import the result.
If it is accepted, selection readiness can be recomputed without rerunning memory
recovery or changing source labels. If it is rejected/unresolved, preserve that
outcome and amend the research design prospectively rather than force a quota.

After qualified data and a correct scoped-provenance cohort are frozen, native
store/order/provenance checks and a costed execution manifest precede the matched
R/C/M/S experiment. The already implemented comparison analyzer will consume its
saved outcomes. **Our ASR, benign-utility effect and selective-transfer benefit
remain unmeasured.**
