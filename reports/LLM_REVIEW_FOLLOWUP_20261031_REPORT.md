# Missing-item LLM review: results and remaining pilot gaps

31 October 2026. **The fixed 160-request follow-up was executed. Automated record
coverage improved from 643/790 to 785/790; five records remain rejected. The
scientific pilot is still not ready.** These are automated proposals, not genuine
human validation or measured defense effectiveness.

## What was completed

- Implemented a versioned one-item review planner, strict decoder, guarded
  transport integration, merged-result checks and offline readiness analysis in
  [the follow-up package](../src/ams/research/llm_followup/README.md).
- Reused all 643 previously accepted record proposals and 35 question assessments
  unchanged. Reviewed every item in the 22 rejected development batches: 147
  records and 13 questions, each once, without showing previous votes/failures.
- Preserved both earlier paid passes, their failed replies, human forms, source
  data, original SAFE-Mem and the primary protocol. No label was changed to meet
  balance, and no additional group was reviewed or selected by method outcomes.
- Prepared an eight-input blinded sample for a later independent quality check
  and an offline inventory of the next seven existing development groups.

The paid version is
[llm_review_followup_v3_1_20261031](../research_data/llm_review_followup_v3_1_20261031/summary.json).
The earlier `llm_review_followup_v3_20261031` is an unrun intermediate plan from
before explicit reference indices were added. Its code fingerprint is stale;
it is preserved and must not be used for execution.

## Coverage and proposed labels

| Endpoint | Before this follow-up | After |
|---|---:|---:|
| Mechanically accepted memory record/use proposals | 643/790 | **785/790** |
| Contributions with complete automated record coverage | 19/32 | **27/32** |
| Question drafts with accepted-format assessments | 35/48 | **48/48** |
| Question drafts passing all five AI criteria | 28 | **40** |
| Complete AI-safe contributions with AI-accepted external claim-backed QA | 8 | **8** |
| Independently human-verified labels/questions | 0/0 | **0/0** |

Of the new requests, 155 passed mechanical validation: 142 records and all 13
questions. Five record responses selected out-of-range evidence-unit indices.
All 160 requests returned `stop`; there were no output-limit or transport failures.
No additional paid retry was made. See the
[missing-item list](LLM_REVIEW_FOLLOWUP_20261031_MISSING_ITEMS.json) and
[raw failures](../research_data/llm_review_followup_v3_1_20261031/review_failures.json).

| Accepted record/use AI proposal | Claims | Evidence chunks | Total |
|---|---:|---:|---:|
| Safe for the specified use | 104 | 507 | **611** |
| Unsafe for the specified use | 31 | 136 | **167** |
| Uncertain | 0 | 7 | **7** |
| Missing/rejected | 1 | 4 | **5** |
| Total actual records | 136 | 654 | **790** |

Complete contribution bundles are **14 AI-safe, 11 AI-unsafe and 2 AI-uncertain**;
five remain incomplete. Safety aggregation concerns external records, keeping
principal-authored statements separate. Proposed source fields were 780 external
and five principal. These source-field proposals do not authenticate authors or
make an innocent uploader culpable.

The newly accepted records include 125 AI-unsafe proposals and 17 AI-safe ones.
All five rejected replies also tentatively proposed unsafe, but those guesses
are not accepted labels. Thus missingness is uneven: the earlier accepted-only
distribution omitted much difficult content. The change from 42 to 167 unsafe
record proposals is not evidence of a higher real attack prevalence, improved
accuracy, new independent incidents or better defense behavior. Multiple rows
can refer to one underlying incident. No label accuracy or FPR/FNR is measured.

## Quality diagnostics and pilot readiness

The [offline feasibility analysis](../research_data/llm_review_followup_analysis_v1_20261031/feasibility.json)
reports eight AI question failures on `no_answer_in_question`; those drafts need
inspection/revision rather than automatic acceptance. Literal external-source
support checks found no mismatch among otherwise AI-accepted candidates. This is
a structural check, not a finding that all references are semantically correct.
There are no detected chunk source-field disagreements in this check; actual
authorship and ambiguous claim entailment are still not independently verified.

The fixed 32-case composition cannot currently satisfy the exploratory requirements:

| Required stratum, per context | Needed | Email complete AI labels / with required QA | File/Document complete AI labels / with required QA |
|---|---:|---:|---:|
| Attack input, AI-unsafe bundle | 8 | 4 / 4 | 5 / 5 |
| Attack input, AI-safe bundle | 2 | 2 / 1 | 4 / 3 |
| Explicit benign input, AI-safe bundle | 1 | 1 / 0 | 0 / 0 |
| Suggestive benign input, AI-safe bundle | 5 | 2 / 0 | 5 / 4 |

Unsafe rows have no benign-question requirement. Original case intent and memory
safety are distinct labels; a proposed unsafe bundle from an originally benign
case is not automatically a measured false positive. Incomplete/uncertain sources
were not counted as safe or used to fill shortfalls. External chunk-only utility
support remains restricted by the frozen baseline configuration. Neither source
availability nor an AI-unsafe record proves actual exposure in an answer context.

[Eight hash-selected input packets](../research_data/llm_review_followup_analysis_v1_20261031/blinded_quality_sample.json)
hide model votes and original case labels for later independent quality checking.
**Completed independent assessments of this sample: zero.** It is not simulated
human validation or an agreement estimate.

The [future development inventory](../research_data/llm_review_expansion_inventory_v1_20261031/inventory.json)
uses the existing group order D01–D07, not proposed labels or historical ASR.
The next group D01 contains **32 contributions, 800 actual memory records and 51
question drafts**. Inventory preparation cost USD 0; no D01 review was dispatched.
Reserved groups D08–D19 were excluded.

## Actual cost and verification

The advance working estimate was USD 0.10–0.40, with maximum-rate full-context
reservation sum USD 4.251648. **Actual additional usage cost: USD 0.05217465**.
Native usage was **515,939 input tokens and 8,469 output tokens** across 160 calls.
The same USD 30 session remains in effect:

- Prior paid reviews: USD 0.10690935.
- Combined paid project usage: **USD 0.15908400**.
- Remaining project allowance: **USD 29.84091600**.
- Pending/unknown/breach attempts and held funds: **zero**.

The first immediate account-usage snapshot differed from the receipt sum; a
subsequent free read-only refresh matched the full USD 0.05217465 delta. Both
snapshots remain saved. Offline completed-run replay left dispatches at 306 and
charges unchanged: **zero additional requests or cost**. See the
[billing/replay reconciliation](LLM_REVIEW_FOLLOWUP_20261031_BILLING_REPLAY.json).

**377 tests and 31 subtests passed**, including 11 new follow-up tests. Targeted
Ruff lint/format checks passed. Tests use invented data and mock HTTP; they do
not establish label quality or safety/utility effects. Before/after fingerprints
cover 1,199 previously existing files; preservation details and final checks are
in the [validation record](LLM_REVIEW_FOLLOWUP_20261031_VALIDATION.json).

No task answers, answer/conflict/target-judge evaluations, training, live trust
updates, new final pilot groups or defense ASR results were produced. Accepted
outputs retain automated/non-human/non-gold/no-live-trust metadata.

## Exact next work

1. Resolve the five reference-invalid records using valid evidence; independently
   assess a blinded quality sample. Preserve all original failed attempts.
2. Review the next fixed development candidates and revise the eight problematic
   question drafts with exact source support. Estimate new calls before spending.
   Do not replace missing external facts with principal preferences or fabricated
   facts, or force labels to obtain the required composition.
3. Once enough eligible AI-labeled development contributions exist, freeze one
   explicitly exploratory 32-case selection, useful question references, checked
   synthetic provenance, shared five-ticket audits and identical probe cohorts.
   Current unknown native origins must not silently become authenticated sources.
4. Execute R/C/M/S at matched feedback and cost, with the same starting memories.
   Compare selective propagation against both contextual and fixed multi-scope
   reputation while measuring retention, restraint, grounded utility and refusals.
5. Independently validate annotation quality and reserve new confirmation groups
   before stronger paper claims. The original human-validated protocol remains
   unfinished. No current result demonstrates selective propagation superiority.
