# Reference-blind question-checker qualification

This workflow uses constructed notes only. It does not read MPBench inputs or
review packets, annotate real memories, train a model, or arm defense execution.

The source/memory extractor receives one passage plus a question. The question
extractor receives only the question. Neither model input contains the proposed
reference answer. Alias comparison happens in the controller afterward; numeric
punctuation, case-sensitive units and negation are preserved. A literal question
exposure rule is conservative. Unmatched paraphrases are not automatically false
facts, and this instrument does not grade arbitrary safety, clarity or usefulness.

```sh
.venv/bin/python scripts/calibrate_question_checker.py prepare --plan research_data/NEW_V1
.venv/bin/python scripts/calibrate_question_checker.py verify --plan research_data/NEW_V1
.venv/bin/python scripts/calibrate_question_checker.py run --plan research_data/NEW_V1
```

`prepare` and `verify` are offline. `run` is paid and requires the advance estimate
and existing shared budget. The plan freezes two 24-case splits, exact expected
checks, prompts, code and thresholds. Development failure leaves validation unused.
Completed results replay; a new folder does not authorize unlimited trials.

The first development run found extra outer ASCII quote delimiters in four model
evidence fields. Its strict version remains failed. A separately frozen decoder
amendment removes one such pair only if the entire inner text exactly matches the
same original input; otherwise it rejects. Raw strings and exact character spans
are saved. No status, answer, rationale, reference or expected label changes.

```sh
.venv/bin/python scripts/validate_question_checker.py prepare \
  --parent research_data/FAILED_DEVELOPMENT_V1 --plan research_data/NEW_V2
.venv/bin/python scripts/validate_question_checker.py run --plan research_data/NEW_V2
```

The amendment must pass the original development gates using saved replies at zero
new development cost, then validate once on the still-unused split. Preparation
rejects a parent whose validation requests have already been dispatched. Any new
decoder revision after validation requires fresh confirmation data.

Both stages must pass every frozen gate before a certificate is written. The
certificate is limited to constructed reference-support and question-exposure
checks. It explicitly sets real MPBench validation, human validation, question
promotion and defense execution to false. A future application needs its own
prospective blinded protocol and unchanged scientific dataset eligibility checks.
