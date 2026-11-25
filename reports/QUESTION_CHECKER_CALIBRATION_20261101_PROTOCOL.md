# Reference-blind question-checker calibration

1 November 2026, Asia/Baku. Freeze before new checker responses. This is an
engineering calibration study on constructed notes, with no MPBench target,
question, expected memory, contributor labels or defense outcomes as inputs.
Previous failed adjudication, human forms and primary protocol remain unchanged.

## Candidate checker

One frozen candidate uses the existing GPT-4o-mini transport and rates. For source
and memory separately, the model receives only a passage and the question. It
extracts an answer with an exact supporting passage quote, or reports not-stated/
uncertain. The proposed reference is hidden from the model. The trusted controller
compares the extracted value with prespecified aliases after whitespace-only
normalization, preserving case, numbers, units and negation. A confirmed result also
needs reference support in the quoted evidence. Unmatched extractions mean
not-confirmed, not a universal proof that a reference is false.

For leakage, the model sees only the question and extracts any answer it supplies
or implies, with an exact question quote. No source, memory or reference answer is
provided. A deterministic whole-token alias exposure rule runs first. Nonliteral
question answers are compared to reference aliases afterward. Unsupported evidence
or ambiguity stays uncertain/invalid; never convert a bad proof into an absent flag.
Literal exposure is deliberately conservative, including an answer in options.

The checker covers reference support and answer leakage. It does not establish
clarity, usefulness, safety of arbitrary instructions, true factual correctness,
human validation or natural-source identity. It cannot automatically label source
records, promote the blocked question, unlock a pilot, or arm defense execution.

## Data, split and frozen gates

Each split has 24 constructed cases: three instances each of direct support,
wrong reference, source/memory disagreement, missing information, conflicting
information, negation, literal question exposure and indirect question exposure.
Development and validation have distinct note identities, values and wording;
they cover the same declared challenge families. This tests constructed cases,
not held-out natural distributions or template-independent generalization.
References and expected results are constructor-only. Exact shared extraction
requests are deduplicated; logical checks and paid requests are reported separately.

Only one prompt/normalization version and one attempt per exact request are allowed.
No prompt tuning, threshold changes or repeated trials after seeing these outputs.
If development fails or execution is incomplete, validation stays unexecuted.
If development passes, run the locked validation once with the same checker.

For EACH split, require all requests valid and complete, at least 44/48 exact
source/memory support decisions, zero false confirmations among expected
not-confirmed or uncertain checks, at least 22/24 supported references confirmed,
all three conflicting-source cases uncertain, and 24/24 question-leakage decisions
correct (including all indirect exposures). Abstaining everywhere cannot pass.
Report integer counts by family, raw evidence and failure reasons. Paired variants
and shared extractions are correlated; do not present them as independent trials.
No general accuracy/FPR/FNR or strong calibration claim follows from this small set.

A certificate is issued only after both splits pass. Its scope is these constructed
support/leakage checks; human validation and MPBench readiness remain false.
Any subsequent real-question assessment needs a new explicit blinded protocol,
preserved earlier votes, fresh controls and unchanged dataset eligibility rules.

## Costs and accounting

Prepare the exact deduplicated job inventory before paid dispatch. Working estimate
for both splits: $0.02–$0.08. Maximum logical inventory before sharing is 138 model
requests (48 support and 21 nonliteral leakage jobs per split); the prepared plan
reports its smaller physical count and full-context reservation sum. These sums
are not assured completion costs. A new actual-spend cap of $0.25 applies to this
calibration, enforced with a full single-request reservation before dispatch.

The existing $30 shared project ceiling remains unchanged; entry spending is
$1.97090205 and remaining allowance $28.02909795. The existing cumulative finishing
cap is retained too. Unknown billing stops new requests. Responses, actual SDK
bodies, costs and failures are durably captured. Completed replies replay without
new charges. No SDK retries, price/model fallback, downloads, training, installs,
new MPBench extraction or live defense evaluation occurs in this workflow.
