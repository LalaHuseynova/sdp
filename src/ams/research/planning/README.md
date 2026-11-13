# Step 11: engineering freeze and conditional pilot cost plan

> Status note — 7 November 2026: This README records the original engineering cost plan. Its proposed USD 125 stop is inactive and superseded by the user’s USD 30 total research allowance. Guarded execution, native stores and shared exact-response reuse now exist and were used in the preliminary study. The final human-validated scientific freeze is still pending. See the [current research guide](../README.md) and [project README](../../../../README.md).

This package freezes the minimum-pilot **engineering settings**, inventories future
jobs, estimates conditional API costs, and reports what is still needed for a
scientific lock. It does not generate final groups, authenticate human reviewers,
run a benchmark, initialize a provider/budget database or enable paid dispatch.

```sh
.venv/bin/python scripts/prepare_dynamic_pilot.py prepare --out research_data/my_new_plan
.venv/bin/python scripts/prepare_dynamic_pilot.py check --bundle research_data/my_new_plan
.venv/bin/python scripts/prepare_dynamic_pilot.py require-scientific-freeze --bundle research_data/my_new_plan
```

The last command intentionally refuses an engineering-only bundle and explains
the missing scientific artifacts. No `--execute` option exists. Existing outputs
are never overwritten; new reviews, code changes or amendments require a new
version. The preparation/check commands run with network connections blocked.

## Frozen choices

The versioned inputs are
[dynamic_pilot_v1.json](../../../../configs/research/dynamic_pilot_v1.json) and
[dynamic_pricing_20261030.json](../../../../configs/research/dynamic_pricing_20261030.json).
The study settings have a canonical version hash; silently changing sample sizes,
model, criteria or execution flags fails validation. The original protocol hash,
official MPBench byte hashes, current original model roles and retrieval settings
are checked. Source, scripts, configuration, prompts, preparation payloads and raw
review files are fingerprinted into the engineering manifest.

- Eight development bags and twelve locked-pilot **slots**; selected scientific
  case IDs remain null until independently reviewed groups exist.
- Three regimes: strong localized (9,9), strong distributed (9,1), null (1,1).
- R/C/M/S at B=5, shared exogenous oracle feedback and no detector/tuning grid.
- Original flat/withhold/hops=0, k=4, m=4, no source cap, sentence endorsement,
  six-claim extraction limit and external evidence off.
- Existing policy weights, thresholds, support gates and fingerprints; original
  prompts/model alias; answer/classifier/conflict/judge output ceilings.
- Utility margins, S-versus-C and S-versus-M comparisons, grouped bootstrap and
  stopping rules. No externally registered preregistration is claimed.

The inventory contains 144 primary and 96 development trajectory slots. It is a
controller artifact, never a model prompt or online source of hidden regime
information. Ordinary case labels, retention/restraint strata and per-use memory
safety are kept distinct. The old provisional case-intent groups cannot supply
verified Z labels or unlock a scientific run.

## Readiness

Preparation checks existing provisional artifacts without regenerating them. It
recomputes review coverage using the current raw Reviewer 1, Reviewer 2 and
adjudicator forms, plus QA reviews, through the existing independent-review
validator. The default review root is `prepared/reviewers`; `--reviews` can name
a new tree with the same `reviewer_1/2/3` structure. Missing reviews remain missing,
not automatically uncertain. Individual labels/references are not copied into
the plan. Structurally valid reviewer attestations are not identity authentication.

A scientific lock still needs actual Z-balanced group manifests, independently
safe source-grounded questions, fixed audit/probe IDs and denominators, real native
graph bindings/response catalogs, local embedding/prompt coverage and the paid
transport/accounting integration. Review counts alone cannot prove those facts.
This preparer therefore emits `scientific_dataset_frozen=false` and cannot promote
its engineering bundle by changing a flag. A separate validated scientific and
execution manifest must be prepared when the real prerequisites exist.

Human review can remain deferred while this setup is completed. The user's session
authorization for needed API work remains recognized; the tool does not invent a
new permission requirement. It makes no paid calls. A future run still needs the
advance estimate, disclosed spending bound and valid execution prerequisites.

## Cost method

Rates were checked against the
[official OpenRouter model page](https://openrouter.ai/openai/gpt-4o-mini/overview):
USD 0.15/M input and 0.60/M output. Refresh them before actual paid use. No provider
cache discounts are assumed. Rates are model-specific and calculated with Decimal;
unknown, missing, zero, negative or nonfinite prices fail rather than become free.

The estimate separates development, locked-primary and combined costs. Working
estimates assume one conflict check per memory query and role-specific input
lengths, with the frozen output ceilings and a 20% retry allowance. Stress uses
six conflict checks per k=4 query, larger input assumptions, at most two attempts
per logical call and another 25% headroom. These are assumptions, not measured
token usage or a statistical confidence interval.

The primary range is 3,888 original questions plus 1,728–2,304 grounded questions.
Across all twenty bags it is 6,480 originals plus 2,880–3,840 grounded questions.
Costs also include:

- One frozen classifier response per exact query/model/prompt: at most 48 per bag.
- All memory answers; no discount for identical answers across methods/regimes.
- Shared no-memory controls for 20 attack inputs and 16 safe-source questions per
  bag. Unused audit-root controls remain diagnostics, not extra scored endpoints.
- Original answer judgments, per-attack retrieved-entry judgments, shared written
  entry diagnostics and no-memory attack judgments. These remain evaluator-only.
- Conflict checks and physical retry allowance, separately from audit tickets.

Shared response provisioning must actually be implemented/verified before assuming
those savings. Otherwise a new, larger estimate is required. A shared cached audit
does not grant S extra evidence or cheaper logical verification; every policy is
charged the same B tickets, including unresolved/copy tickets.

Fresh extraction is not a planned paid fallback: memory versions must already be
frozen and reviewed. A miss aborts; replacement records require reannotation and an
amended plan. Embeddings use an already installed/cached local MiniLM only. The
minimum oracle pilot has zero paid detector/verifier calls, with human annotation
cost explicitly unknown. Grounded QA uses validated aliases and blinded human
review for semantic cases, rather than assuming free LLM judgments.

The proposed combined stop cap is **$125**, inactive. It covers the displayed
assumption-based stress estimate, not every possible 128K-context call. The JSON
also gives the much larger full-context/all-attempts reservation calculation.
The existing durable GPT-4o-mini guard reserves before physical dispatch, retains
unknown-outcome holds and restricts price/fallback behavior; it is not yet connected
to the offline sequential runner. A future run must stop at the spending limit
and report incomplete coverage, rather than claim completion or safety from failure.

Real verifier studies, new extraction/reannotation, hyperparameter grids, optional
reference arms, robustness suites, a second model and full MPBench are excluded and
need their own estimates. Taxes, credit purchase fees, annotation/adjudication labor
and local compute are also excluded. This is an API planning estimate, not a paper
budget, active allowance, guaranteed bill or guarantee of scientific efficacy.
