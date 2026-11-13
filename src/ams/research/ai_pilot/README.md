# AI exploratory pilot gate

> Status note — 7 November 2026: The failed question-validation gate below remains failed. A later, separately declared provisional comparison ran without source-grounded utility-QA scoring; it did not bypass this gate to claim a validated utility set. See the current project results for that narrower scope. See the [current research guide](../README.md) and [project README](../../../../README.md).

`adjudication.py` implements one frozen, blinded question-review round. It does
not authenticate contributors, invent human reviews, change record safety labels,
or arm defense execution. It uses the existing capped, durable annotation transport.

```sh
.venv/bin/python scripts/adjudicate_ai_questions.py prepare \
  --plan research_data/NEW_VERSION \
  --reviews research_data/EXISTING_ACTIVE_VIEW
.venv/bin/python scripts/adjudicate_ai_questions.py run \
  --plan research_data/NEW_VERSION
.venv/bin/python scripts/adjudicate_ai_questions.py view \
  --plan research_data/NEW_VERSION \
  --reviews research_data/EXISTING_ACTIVE_VIEW \
  --out research_data/NEW_DERIVED_VIEW
```

Preparation is offline. Running is paid and needs the advance cost estimate and
existing project budget. Reopening a completed plan reuses saved results. A new
directory is a new plan, not permission for extra rounds or a reset allowance.

All unsettled, non-rejected active question checks enter the target set. Eight
seeded, source-distinct real controls and four constructed controls are intermixed
without exposing roles, old verdicts or quotas. All synthetic checks must pass.
Only target versions can enter the derived active view; real-control votes stay
audit-only. Uncertainty and literal answer leakage cannot produce a pass.

Use `scripts/finish_ai_pilot.py readiness` on the derived view before any freeze.
The source-bundle, external-claim, template and category requirements still apply.
The primary human-validation gate remains unchanged. A successful AI data freeze
would still need cache-only native-store validation and a distinct checked, costed
AI execution manifest before an R/C/M/S comparison.

On 1 November the first round failed three constructed checks. No target version
was promoted; readiness stayed false. Preserve that result rather than retrying
the target until it passes. See the versioned report in `reports/`.
