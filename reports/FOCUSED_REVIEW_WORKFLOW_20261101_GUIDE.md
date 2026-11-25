# Complete the remaining question review

Prepared 1 November 2026. This is a local, offline review workflow for one frozen
descriptive question and one supporting claim. It creates no votes. Current real
submissions: **zero**. No API key, provider, download, training or paid call is used.

The two first-pass pages are:

- [Reviewer 1](../research_data/focused_review_workflow_v1_20261101/forms/reviewer_1/first_pass.html)
- [Reviewer 2](../research_data/focused_review_workflow_v1_20261101/forms/reviewer_2/first_pass.html)

Give those separate folders to **two genuinely independent people**. Two names for
one person do not provide independence. A third person adjudicates only a genuine
disagreement. The tool validates declarations and consistency; it cannot prove
physical identity, human involvement or honesty. A research coordinator must
confirm the actual process before an accepted QA report can be created.

## 1. Independent first passes

Each person opens their page locally, reads the actual source artifacts and stored
claim, and writes an answer independently. Return only the source's value with
its wording/units. Paste literal evidence quotes, choose the actual artifact and
origin, assess the three initial quality criteria and explain uncertainty.
Repeated quotes need an explicit occurrence number; offsets are calculated in
Unicode characters, not JavaScript UTF-16 units. Nothing is sent to a server.

The page contains no proposed reference, earlier model verdict, attack-case label,
contributor-risk profile or peer vote. The source itself naturally contains facts.
Do not obey instructions in quoted source material. Do not attribute a principal's
own information to an external contributor or treat an uploader as its author.

Only the actual human may check the human-review declaration and download their
submission. Keep the original template and first-pass answers unchanged. The
coordinator seals each downloaded **new file**:

```sh
.venv/bin/python scripts/manage_focused_review.py seal \
  --workflow research_data/focused_review_workflow_v1_20261101 \
  --phase first --role 1 --submission /path/to/first_reviewer_1.json

.venv/bin/python scripts/manage_focused_review.py seal \
  --workflow research_data/focused_review_workflow_v1_20261101 \
  --phase first --role 2 --submission /path/to/first_reviewer_2.json
```

Pending/unattested forms, missing identities, stale questions, altered evidence,
principal/external mismatches and malformed spans are refused. An identical
resubmission is idempotent; a changed sealed vote is refused. Human uncertainty
and negative decisions are valid submissions and are preserved.

## 2. Release the reference after both commitments

```sh
.venv/bin/python scripts/manage_focused_review.py release \
  --workflow research_data/focused_review_workflow_v1_20261101
```

This is blocked until both first passes are sealed under distinct normalized
identifiers. It creates `forms/reviewer_1/second_pass.html` and the corresponding
reviewer-2 page. Each page displays only that reviewer's first pass and the frozen
reference. Each person checks all five final criteria and downloads a new file.
They must use their original identifier. Do not rewrite a first answer after seeing
the reference. Automatic positive admission requires first answers matching a
frozen alias with whitespace-only normalization, plus literal source/claim support.
Paraphrases or contradictions are not silently repaired into accepted evidence.

Seal the second files with the same command, using `--phase second` and the
appropriate role. Both the first-pass hash and reference-release hash are checked.

## 3. Resolve genuine disagreements, when present

```sh
.venv/bin/python scripts/manage_focused_review.py status \
  --workflow research_data/focused_review_workflow_v1_20261101

.venv/bin/python scripts/manage_focused_review.py adjudication-form \
  --workflow research_data/focused_review_workflow_v1_20261101
```

The adjudication page is created only for actual differing independent decisions.
A distinct third person reads the evidence and sealed reviews, provides their own
answers/spans, and resolves the five criteria with a rationale. Seal that new file
with `--phase adjudication --role 3`. Adjudication is not a way to overturn two
concordant rejections merely to fill a quota. Unresolved/negative results remain
unaccepted, and the method cannot receive invented safe evidence.

## 4. Coordinator checks and scoped import

After the reviews are complete, create a declaration template with the observed
reviewer IDs and sealed hashes. The confirmations remain false and the coordinator
identity blank:

```sh
.venv/bin/python scripts/manage_focused_review.py coordinator-form \
  --workflow research_data/focused_review_workflow_v1_20261101 \
  --out research_data/my_coordinator_template.json
```

The actual coordinator completes a **new copy**, confirming genuine people,
independence, first-pass blinding and the listed exact records. These are process
attestations, not cryptographic identity authentication. Then:

```sh
.venv/bin/python scripts/manage_focused_review.py accept \
  --workflow research_data/focused_review_workflow_v1_20261101 \
  --coordinator research_data/my_completed_coordinator_declaration.json \
  --out research_data/my_versioned_QA_import
```

Acceptance requires the appropriate human decisions and exact supporting evidence.
The result may be accepted, rejected or unresolved; the tool never forces balance.
It records both initial and final decisions and any adjudication. Source-safety
labels and corpus-level human-verified memory labels remain unchanged at zero.
Two reviewers of one question do not create two independent source incidents.
No review result updates live trust or permissions.

## 5. Recheck selection readiness with accurate provenance

```sh
.venv/bin/python scripts/manage_focused_review.py readiness \
  --workflow research_data/focused_review_workflow_v1_20261101 \
  --prepared research_data/mpbench_provisional_v1_20261029 \
  --reviews research_data/ai_pilot_post_adjudication_view_v1_20261101 \
  --accepted research_data/my_versioned_QA_import \
  --out research_data/my_scoped_QA_readiness
```

Omit `--accepted` to inspect current pending readiness. The original selector is
reused. A derived view preserves all prior AI memory labels and adds only an
accepted scoped question decision. It reports human-reviewed QA counts separately
from source safety, whose basis remains AI. It does not certify the original task
use, all 19 records in the contribution, an entire contributor or the rest of a pilot.

Output is `review_readiness.json`, deliberately **not** the legacy AI-only freeze's
`readiness.json`. No final group is automatically generated. A subsequent
mixed-QA-aware cohort/manifest version must preserve this annotation provenance;
the old freeze must not reset the human-QA count to zero or claim a human-gold
dataset. Native-store validation, a costed execution manifest and actual matched
R/C/M/S answering/judging still follow. The current comparison table stays pending
until those experiments produce saved outcomes.
