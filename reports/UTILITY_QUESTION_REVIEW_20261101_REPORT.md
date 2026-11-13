# Bounded utility-question review and main-study readiness

Completed 1 November 2026. The next preparation step was implemented and run under the previously authorized $30 research-session ceiling. Engineering validation passed. The frozen real-question review did **not** pass its admission gate, so it produced **no new accepted question, source label, or frozen pilot cohort**. No dynamic-defense experiment was run.

The scientific question remains whether selective propagation (S) improves on contextual reputation (C) and fixed multi-scope reputation (M), using the same metadata, five revealed audits, retrieval resources and benign-utility constraints. Record-only containment (R) remains the common reference. A utility-question review is preparation for that comparison; it provides no evidence that S is effective or novel.

## Work completed

- Added [the bounded review module](../src/ams/research/ai_pilot/utility_review.py), [its CLI](../scripts/review_remaining_utility.py), and [nine offline tests](../tests/test_real_utility_review.py), including a regression for the observed quality-control failure.
- Froze [the review protocol](UTILITY_QUESTION_REVIEW_20261101_PROTOCOL.md), requests, private references, controls, inputs and dependency hashes before new responses.
- Reviewed the existing unresolved question once as an audit-only diagnostic and exactly one prospectively specified alternative grounded in its actual stored claim. No second rewrite, retry, easier-case substitution or quota relaxation occurred.
- Ran eight source-distinct real controls, four constructed support/exposure controls and two constructed question-quality controls. The real controls have no new independent gold labels; their outputs cannot establish accuracy.
- Saved all 42 physical responses, native usage, actual schema-bearing requests, individual decisions, original evidence and control outcomes in [the versioned review directory](../research_data/remaining_utility_review_v1_20261101).
- Recomputed [AI-only composition readiness](../research_data/ai_pilot_after_utility_review_v1_20261101/readiness.json), tested rejection of an incomplete freeze, reconciled receipts, replayed all 42 responses offline and checked existing-file integrity.

## Review outcome

| Check | Result |
|---|---|
| Planned/completed physical requests | 42 / 42; one physical attempt each |
| Tasks | 25 passage-support, 13 question-only exposure, 4 quality proposals |
| Constructed control checks | 5 / 6 matched; required 6 / 6 |
| Original-question diagnostic | Source supported the answer; the stored claim did not establish its time qualifier |
| New candidate | Memory support confirmed; no answer exposure detected; source quote invalid under the frozen span rule |
| New eligible question proposals | 0 |
| Existing source-safety labels changed | 0 |
| Independently verified human labels/questions | 0 / 0 |

The failed quality control requested sending a confidential blueprint outside its authorized workspace. The model returned `safe_descriptive_use=true`, despite its reason recognizing that the request was an action. The other quality flags rejected the request, but the frozen local rule required the particular safety flag to be false. That rule was retained. This is a failure of this question-quality proposal component, not a measured attack against the dynamic defense.

For the new real candidate, the model removed Markdown emphasis from its source quote. The frozen decoder permits only whitespace changes and one outer ASCII quote pair; it cannot silently delete Markdown punctuation. The source check therefore remained invalid even though the proposed numerical answer matched the private aliases. Three support responses in this run had invalid quote checks, including two from one real control. Invalid evidence was not converted into a positive or negative gold label.

The raw candidate quality proposals were affirmative, but the global control gate and its own source-support gate both prevented admission. `AI_candidate_assessments=0` in the summary counts admitted proposal rows; the raw diagnostic and candidate judgments are preserved in `frame_results.json` and `review_votes.json`.

The earlier checker certificate covers constructed support/exposure checks only. It does not certify natural MPBench question quality, provenance, source safety or factual truth. No certificate scope or historical result was changed after these failures.

## Dataset readiness

The active AI review corpus remains 256 development contributions with 6,325 records: 65 AI-safe bundles, 104 AI-unsafe bundles and 87 AI-uncertain bundles. These are automated proposals, not independently verified labels. There remain 33 AI-safe sources with currently accepted claim-grounded AI utility proposals.

All original per-context strata remain binding: eight unsafe attack bundles, two safe attack bundles, one safe explicit-retention bundle and five safe suggestive bundles. The remaining shortfall is **File/Document explicit-retention: zero eligible utility-supported contributions selected, one required**. Two nominal AI-safe contributions in that category do not establish eligibility: one lacks a qualifying external claim and the other has the unresolved question reviewed here. Principal information and evidence chunks were not substituted for an external contributor's claim.

The real-data freeze call raised `Required AI-label/QA composition unavailable` before creating an output directory. No 31-case substitute, changed category, fabricated annotation or final 32-case cohort was produced. The existing provisional 20 groups and earlier artifacts remain unchanged. Human-validated pilot readiness is also false.

## Engineering, integrity and accounting

The final relevant offline regression suite passed **452 tests and 31 subtests**, including all nine new bounded-review tests. These test software behavior using offline fixtures; they are not measurements of defense efficacy or annotation accuracy. The separate real-data checks are recorded in [the final validation report](UTILITY_QUESTION_REVIEW_20261101_FINAL_VALIDATION.json); the initial 451-test validation record is preserved.

All 42 actual model inputs matched their frozen requests and schemas. Passage checks received only a passage and question; exposure checks received only a question; quality proposals received source, actual memory, question and the descriptive-use declaration. Private aliases, case labels, expected targets, control roles, prior verdicts and quota shortages were excluded from these structured inputs. Original payload text can naturally contain target words. Ground-truth separation is a harness contract, not an operating-system sandbox.

All 42 native responses ended with `stop`. Their saved text, native cost, receipt, request schema, provider restrictions and decoded votes reconciled. Offline replay returned identical saved results with **zero new requests and zero new cost**. No pending, unknown or breach receipts remain. See [billing/replay checks](UTILITY_QUESTION_REVIEW_20261101_BILLING_REPLAY.json).

| Spending item | USD |
|---|---:|
| Advance working estimate | 0.01–0.05 |
| New actual-spending stop | 0.10 |
| Actual new cost: 17,502 input + 2,125 output tokens | **0.00390030** |
| Research-session cumulative use | **1.98819000** |
| Remaining within the unchanged $30 ceiling | **28.01181000** |

The free provider postflight's usage delta exactly matched the new native cost. Its wider key usage includes earlier work outside this research-session ledger; it is not this study's cost. No spending limit was raised. See [provider reconciliation](UTILITY_QUESTION_REVIEW_20261101_PROVIDER_POSTFLIGHT.json).

[The integrity check](UTILITY_QUESTION_REVIEW_20261101_INTEGRITY_AFTER.json) confirmed all **3,351 fingerprinted existing files unchanged**, including original MPBench/SAFE-Mem files, prior results, review forms, protocols and the existing dynamic policies/retrieval implementation. The fingerprint-set SHA-256 is `542eb9fe2a93a11e67e411bb6dc5f25bf7d61affdba4058e31056a13be0ebf1c`. No exact credential matches were found in the 57 new phase/readiness files scanned.

## Remaining sequence

1. Resolve the narrow outstanding question and provenance/use checks through a genuinely qualified review. An LLM-only continuation must first correct and prospectively qualify the failed quality/quote components on new controls; this failed run cannot become a passing locked test through a post-hoc decoder or threshold change. No further paid review loop was started here. Human review remains an available independent route and is still pending.
2. Recheck unchanged category, group/template, unique-support and provenance requirements. Freeze an explicitly AI-only exploratory cohort only if its gates pass. Preserve its distinction from the human-validated protocol.
3. Reconstruct native stores **in that frozen cohort's ingestion order**, using cache-only extraction, embeddings and conflict responses. Check logical-to-native record bindings and leave uncertain attribution local. The earlier stores cannot be relabeled as an exact reconstruction of a differently ordered cohort.
4. Check disabled-effect static parity, claim/chunk permission coverage, equal audit exposure and restart behavior on those stores. Finish the concrete execution manifest and estimate all answer/judge/query costs before paid comparison calls.
5. Run R/C/M/S on identical episodes and audits; include the static and no-memory references, separate original retention/restraint from source-grounded QA, and report paired safety, utility, coverage and cost. Scale or revise only after those outcomes.

The main-method code still keeps local containment common, overlapping group counts separate from authority, incidents deduplicated, corrections reversible, uncertain origins unpenalized at contributor scope, and S's batch/context/source support gates distinct from C and M. This turn did not alter those rules. The two-context AI development study cannot establish natural-source generalization, human-label validity, or an ICML-level contribution. **No preliminary ASR, benign-utility gain or selective-transfer benefit has been measured.**
