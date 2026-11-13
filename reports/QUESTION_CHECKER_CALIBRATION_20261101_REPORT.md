# Reference-blind question checker implemented and qualified on constructed cases

1 November 2026, Asia/Baku. **The final checker passed one fresh, 24-case constructed confirmation set: 48/48 source/memory support checks and 24/24 question-leakage checks, with zero false confirmations and zero invalid evidence fields.** It has not been validated on MPBench or by humans. No real question was promoted and no defense experiment ran.

The implementation fixes the earlier reviewer's conflation of answers in a source with answers in a question. The proposed reference is hidden from every model request:

- For source and memory support, the model sees one passage and the question, then extracts a specific answer with quoted evidence or reports missing/uncertain information. The controller compares the extracted answer with private, frozen aliases afterward.
- For question exposure, the model sees only the question and extracts any answer that the question supplies or implies. Source, memory and reference fields are absent. A deterministic literal-exposure check runs first; indirect extracted values are compared afterward.
- The span decoder retains every model status, answer and rationale. It maps permissible presentation differences to exact original Unicode-character offsets. Only whitespace normalization and one outer ASCII double-quote pair are allowed. Digits, punctuation, case-sensitive units and negation are preserved.

This instrument checks reference support and answer exposure. It does not establish arbitrary memory safety, source authority, real-world factual truth, human validation, task usefulness or natural-author authentication.

## Development and fresh confirmation

The original [protocol](QUESTION_CHECKER_CALIBRATION_20261101_PROTOCOL.md) defined two 24-case constructed splits and fixed gates. Each split has three instances of direct support, wrong references, source/memory disagreement, missing information, conflicting information, negation, literal question exposure and indirect question exposure. References, expected decisions and challenge-family labels stay private. Public note identities are opaque and do not encode the family.

| Version and stage | Support correct | Leakage correct | Invalid logical checks | Outcome |
| --- | ---: | ---: | ---: | --- |
| V1 development, strict evidence strings | 47/48 | 21/24 | 4 | Failed; validation remained unused. |
| V2 locked validation, one exact outer-quote-pair decoder | 44/48 | 24/24 | 4 | Failed; its result remains unchanged. |
| V3 fresh confirmation, exact spans with whitespace mapping | **48/48** | **24/24** | **0** | Passed all frozen gates. |

V1's four invalid fields contained extra quotation marks around otherwise exact input text. The [V2 amendment](QUESTION_CHECKER_CALIBRATION_20261101_QUOTE_AMENDMENT.md) was developed on saved development replies before validation. It did not change prompts, model answers, expected labels or thresholds. V2 passed the development recheck offline, then ran the unused validation once.

V2's four invalid fields replaced U+00A0 spaces with ordinary spaces. Its validation also had only 21/24 positive reference confirmations, below the required 22/24. It was not certified or retroactively reported as passing.

The [final prospective protocol](QUESTION_CHECKER_CALIBRATION_20261101_FRESH_CONFIRMATION.md) explicitly reclassified BOTH consumed sets as development data for V3. It added a deterministic whitespace-to-original-span map, preserving the failed V1/V2 artifacts. The 108 old replies were re-evaluated offline without new model calls. Their results do not count as V3 confirmation evidence.

V3 was frozen before 24 new confirmation cases were dispatched. The new cases have new note identities, cities and numerical values, thin-space formatting, MB/Mb unit distinctions and inverse weekday clues. No source/memory/question triple or request identity overlaps either earlier set. The same challenge families are shared, so this is not template-independent or natural-data generalization. No further qualification round followed the final confirmation.

The unchanged gates require at least 44/48 exact support decisions, zero false confirmations on expected non-confirmed/uncertain checks, at least 22/24 supported references confirmed, all three conflicting-source cases uncertain, all 24 question checks correct and no invalid checks. The final set achieved 48/48 support, 24/24 supported references confirmed, 3/3 conflict abstentions and 24/24 question checks. Three literal-exposure checks are deterministic; 21 use question-only model extractions.

[Fresh results](../research_data/question_checker_confirmation_v3_20261101/confirmation_results.json), [raw/evidence-aligned votes](../research_data/question_checker_confirmation_v3_20261101/confirmation_votes.json), and [scope-limited certificate](../research_data/question_checker_confirmation_v3_20261101/checker_certificate.json) preserve the final observations. The certificate explicitly leaves `MPBench_validated`, `human_validated`, `may_promote_questions` and `defense_execution_enabled` false.

## Delivered code and validation

- [Reference-blind extraction and constructed study](../src/ams/research/ai_pilot/calibration.py).
- [Quote-only development amendment](../src/ams/research/ai_pilot/calibration_v2.py) and [exact quote alignment](../src/ams/research/ai_pilot/quote_alignment.py).
- [Final fresh-confirmation controller](../src/ams/research/ai_pilot/confirmation.py) and [Unicode whitespace/span mapper](../src/ams/research/ai_pilot/whitespace_alignment.py).
- Three versioned CLIs: [calibrate](../scripts/calibrate_question_checker.py), [validate](../scripts/validate_question_checker.py), [confirm](../scripts/confirm_question_checker.py).
- Tests for [reference isolation/stage gates/budget stops](../tests/test_question_calibration.py), [quote alignment/unused-validation protection](../tests/test_question_quote_alignment.py), and [Unicode spans/fresh-data protection](../tests/test_question_whitespace_alignment.py).

**443 tests and 31 subtests passed offline in 43.34 seconds.** Targeted lint and formatting checks passed. These tests include correct and deliberately wrong mock model outputs. They do not fabricate human reviewers. Completing/reopening a plan reuses saved replies; preparing the same consumed validation or confirmation as a new trial is rejected.

All 162 unique model replies were separately checked with the final span mapper. There were 110 nonempty evidence spans and 52 empty evidence fields. The final mapper used 95 exact matches, 11 matches after removing one outer quote pair and four whitespace-only matches. Every returned span equals the exact original input substring. Zero model statuses, answer values or rationales were altered. Empty evidence is an allowed explicit missing/uncertain/question-not-given outcome, not a fabricated quote.

A read-only verification of the completed final plan is:

```sh
.venv/bin/python scripts/confirm_question_checker.py verify \
  --plan research_data/question_checker_confirmation_v3_20261101
```

Original SAFE-Mem, official MPBench payloads, old annotations/forms and earlier reports were preserved. All **3,131 inventoried pre-existing files** remain unchanged. The exact-credential scan found no matches in the 220 inspected calibration artifacts at audit time.

## Actual API costs

| Paid stage | Requests | Actual cost |
| --- | ---: | ---: |
| V1 development | 54 | $0.00449160 |
| V2 first validation | 54 | $0.00440820 |
| V3 fresh confirmation | 54 | $0.00448785 |
| **This task total** | **162** | **$0.01338765** |

Offline development rechecks added zero calls and zero cost. Identical passage extractions were shared: the 162 physical requests comprise 99 passage-extraction calls and 63 question-only calls. Logical source/memory checks and paired variants are correlated; they are not 162 independent natural examples.

Entry project spending was $1.97090205. Current project spending is **$1.98428970**, leaving **$28.01571030** within the unchanged $30 project limit. The cumulative $0.25 calibration stop and earlier finishing guard stayed active and were not reset. All 162 native finish reasons were `stop`; usage was 57,423 input and 7,957 output tokens. Native costs, durable receipts and the free provider-usage delta agree exactly. There are no pending, unknown or breached receipts.

Actual SDK messages/schema/model/generation/routing and maximum prices were checked. Serialized inputs contain only passage/question or question, with no proposed answer, expected decision, prior vote, split or family label. Natural occurrence of the correct value inside the provided passage is legitimate task content. No model download, dependency installation, training or new memory extraction occurred.

Replaying all 54 completed final requests with networking blocked made zero extra calls and cost zero. All 1,625 project dispatches are complete.

[Software/result validation](QUESTION_CHECKER_CALIBRATION_20261101_VALIDATION.json), [billing/replay](QUESTION_CHECKER_CALIBRATION_20261101_BILLING_REPLAY.json), [provider reconciliation](QUESTION_CHECKER_CALIBRATION_20261101_PROVIDER_POSTFLIGHT.json), and [integrity/span checks](QUESTION_CHECKER_CALIBRATION_20261101_INTEGRITY_AFTER.json) provide machine-readable evidence.

## Research status and next use

| Item | Status |
| --- | --- |
| Replacement support/leakage checker | Implemented. |
| Fresh constructed qualification | Passed, with the limitations above. |
| Existing blocked MPBench question | Not re-reviewed in this calibration study. |
| MPBench safety labels / genuine human validation | Unchanged; zero human-verified labels/questions. |
| Final 32-case cohort, native construction and R/C/M/S evaluation | Still pending the real-question eligibility decision and the existing gates. |

The next application is a separately frozen, blinded review of the unresolved real utility question with fresh controls and preserved prior votes. It must use the fixed qualified decoder and reference-blind requests. Clarity, usefulness, safe intended use, external-claim attribution and the complete source-bundle requirement remain separate checks. A component certificate cannot replace them or automatically unlock the pilot.

The scientific pilot still requires its declared validated inputs. An AI-only exploratory cohort needs an explicit prospective annotation protocol and all composition/utility gates, then cache-only native-store/binding validation and its own checked, costed execution manifest before paid R/C/M/S comparisons. Every arm must receive identical feedback and verification resources.

The constructed results do not measure natural MPBench grader accuracy, malicious-memory detection, calibrated source-risk probabilities, ASR, benign task utility or selective-propagation benefit. Evidence matching does not authenticate an author or establish arbitrary entailment. The small, deliberately clear synthetic cases and shared families limit generalization; representative independent real annotations remain necessary for stronger research claims.
