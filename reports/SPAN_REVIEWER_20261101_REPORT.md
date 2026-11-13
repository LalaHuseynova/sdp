# Exact-span reviewer revision: implemented, qualification failed

Completed 1 November 2026, Asia/Baku. The next reviewer revision was implemented,
tested offline and subjected to one frozen qualification run. **It did not qualify.
No real-question application, accepted question or pilot freeze followed.** The
earlier failed run remains unchanged. No further paid revision was started.

The research question remains selective provenance propagation (S) versus contextual
reputation (C) and fixed multi-scope reputation (M), with record-only containment
(R), equal B=5 feedback, shared metadata and preserved benign utility. No method,
source-safety label, authority rule, permission or original MPBench payload changed.

## Implemented work

- [Exact-span reviewer module](../src/ams/research/ai_pilot/span_review.py) and
  [CLI](../scripts/review_exact_spans.py), with [18 new offline tests](../tests/test_span_reviewer.py).
- A support interface that returns IDs for verbatim source lines. The controller
  retrieves the original Unicode spans without deleting Markdown or repairing
  content. A returned answer must match the private reference and appear in the
  selected original line for confirmation.
- A separate requested-use classification: descriptive report, action/external
  disclosure, principal preference/authority, or unclear. Descriptive eligibility
  is derived from that class rather than a model's safety boolean.
- [A prospectively frozen protocol](SPAN_REVIEWER_20261101_PROTOCOL.md), 24 new
  constructed support/exposure cases and 12 quality controls. Constructed instances
  are new within known families; they do not establish natural-case generalization.
- A conditional application using exactly the same previously frozen real question,
  source, claim, aliases and provenance. No second rewrite or new case selection.
  Its unchanged question-only check was eligible for exact cached replay, but the
  application gate never opened, so even that replay was not consumed in the run.
- [A focused, blank review package](../research_data/focused_utility_review_pending_v1_20261101/README.md)
  for the remaining question: two independent reviewer folders, an adjudicator
  folder, original sources/claim, first-pass answer/evidence fields and privately
  separated proposed references. **Zero genuine reviews are completed.** This is a
  local handoff, not an automatic importer or a certification of the other records.

The review plan and all individual responses/decisions are preserved in
[the versioned phase directory](../research_data/span_reviewer_v2_20261101).

## Qualification outcome

| Component | Observed | Frozen requirement |
|---|---:|---:|
| Correct support decisions | 47/48 | At least 44/48 |
| Positive support confirmations | 24/24 | At least 22/24 |
| False support confirmations | **1** | **0** |
| Unresolved source conflicts returned uncertain | **2/3** | **3/3** |
| Question-exposure decisions | 24/24 | 24/24 |
| Malformed/invalid checks | 0 | 0 |
| Quality-control cases meeting every declared check | **9/12** | **12/12** |

The evidence-format mechanism worked on the constructed run: all responses were
valid and the selected original spans could be checked literally. Semantic support
still failed. In one example, two equally authoritative entries reported `5.9 GB`
and `5.9 Gb`, explicitly without priority or resolution. The model selected the GB
entry and confirmed that reference. The controller preserved this as a false
confirmation. Correct quotation alone does not establish a correct interpretation.

Requested-use classifications matched all ten controls with a specified use class,
including the action/disclosure controls. Two word/character-count questions were
incorrectly marked useful. For an ambiguous request, the model correctly selected
`unclear` but returned null clarity, whereas the frozen control required false.
That conservative abstention also counts as a failed control under this plan; the
other failures remain substantive. No requirement was relaxed after seeing it.

All 84 qualification calls completed. The four real-question checks were withheld,
all old AI labels/votes remained unchanged, and the new proposal file is empty.
The quality and support failures are component-validation findings, not measured
attack outcomes or evidence for/against selective propagation.

## Engineering and spending checks

The full relevant regression suite passed **470 tests and 31 subtests**, including
the 18 new tests. Coverage includes private-reference isolation, verbatim span IDs,
wrong/duplicate evidence, use classification, conditional stage rejection, a zero
budget stop, exact cached-question replay, restart behavior and no human/gold
promotion. [Offline test record](SPAN_REVIEWER_20261101_OFFLINE_TESTS.json).

The live run comprised 48 support, 24 exposure and 12 quality requests. All native
responses ended with `stop`. The 84 actual requests matched frozen inputs and
schemas, provider/rate restrictions, saved native responses and settled receipts.
All 84 replies replayed offline with **zero new requests or cost**. No pending,
unknown or breach receipts remain. [Billing/replay audit](SPAN_REVIEWER_20261101_BILLING_REPLAY.json).

| Spending item | USD |
|---|---:|
| Advance working estimate | 0.01–0.06 |
| Additional actual-spending stop | 0.15 |
| Actual: 32,984 input and 3,677 output tokens | **0.00715380** |
| Research-session cumulative use | **1.99534380** |
| Remaining within unchanged $30 limit | **28.00465620** |

The free provider postflight delta matched the new native charge exactly; the
broader key limit was unchanged. Broader key usage includes earlier work outside
this research-session ledger. [Provider check](SPAN_REVIEWER_20261101_PROVIDER_POSTFLIGHT.json).

All **3,420 fingerprinted pre-existing files** were preserved, including the earlier
failed reviews, source data, Original SAFE-Mem, protocol/proposal, dynamic ledger,
comparison policies, retrieval code and human templates. No exact credential match
was found in the new phase/review artifacts. [Integrity check](SPAN_REVIEWER_20261101_INTEGRITY_AFTER.json).

## Current readiness and next action

The corpus remains 256 development contributions with 6,325 AI-reviewed records:
65 AI-safe bundles, 104 AI-unsafe bundles and 87 AI-uncertain bundles. These are not
independently verified human labels. There remain 33 AI-safe sources with currently
accepted claim-grounded AI utility proposals. No accepted label/question counts
increased in this step.

The unchanged 32-case composition remains short of **one eligible File/Document
explicit-retention contribution with a qualifying external-claim utility question**.
The fresh readiness check is false, and attempting the freeze is rejected before
an output directory is created. No quota, source, question or label was substituted.
[Readiness/rejection check](SPAN_REVIEWER_20261101_READINESS_CHECK.json).

The concrete next action is a qualified, independent review of that remaining
question and its provenance/use. The focused package makes that work reviewable
without submitting every preparation packet at once. Two genuine independent
reviewers and, when needed, an adjudicator can use its blank forms. Another LLM
reviewer would require a separately declared qualification; this model run is not
a passing certificate. The new descriptive-use question must not be used to certify
the original task use or every sibling record. Human-validated corpus labels remain
at zero.

After the relevant gates pass, recheck unchanged category/template/unique-support
requirements and freeze the explicitly AI-only exploratory cohort. Then reconstruct
native stores in its actual ingestion order, verify provenance bindings, static
parity and restart, and freeze a costed matched R/C/M/S execution manifest. No
benchmark answering/judging, training or dynamic-defense effectiveness experiment
was performed here. **ASR, benign-utility effects and selective-transfer benefits
remain unmeasured.**
