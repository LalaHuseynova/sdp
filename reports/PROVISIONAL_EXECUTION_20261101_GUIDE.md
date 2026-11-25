# Provisional execution preparation with human review deferred

Prepared 1 November 2026. Human review remains pending. This step prepares and
checks an execution contract; it makes **no paid model calls, audit findings,
retrieval experiments or performance results**.

## Scope and commands

The prepared output is
[`research_data/provisional_execution_path_v1_20261101`](../research_data/provisional_execution_path_v1_20261101/preparation_report.json).
It reuses existing development bag D00, its 32 original inputs and cache-built
native store, with strong/localized, strong/distributed and uninformative
overlays. No input group was selected using method performance or resampled.

```sh
.venv/bin/python scripts/prepare_provisional_execution.py verify \
  --plan research_data/provisional_execution_path_v1_20261101
```

To prepare a fresh version, use a new destination:

```sh
.venv/bin/python scripts/prepare_provisional_execution.py prepare \
  --pricing configs/research/provisional_pricing_20261101.json \
  --bag D00 \
  --out research_data/my_new_provisional_execution_plan
```

There is no `run` command, credential argument, new budget initialization or
automatic cache fallback. The CLI uses the existing offline network guard.
Other existing development bags can be requested explicitly; reserved unvalidated
bags are refused. Any changed source, code, memory payload or spending snapshot
requires a new plan rather than rewriting this output.

## What is checked

The existing 20-store native bundle passes its 62 payload and 442 dependency
checks. The D00 native graph is restored and checked against its actual public
contributions and private construction crosswalk: **136 claims, 654 chunks and
1,195 source bindings**. Claim/chunk text hashes, source spans, contribution
membership, policy parents and principal/external separation must match.

Only the private original identifier key is used to join native logical IDs to
already blinded public IDs. Public IDs are not blinded a second time, and display
headers or lexical similarity cannot become join keys. The key is not copied
into the plan.

Each planned arm gets a fresh mutable graph/client/classifier instance with the
same non-policy initial state. The episode ingestion order must match the store
exactly. The 31 distinct scheduled query texts have exact classifier and embedding
cache entries; no classification or retrieval is executed to check that fact.
Input/state parity is checked; equality of actual retrieved contexts or answers
is not claimed without running queries.

## Fair input and audit contract

Every regime has the same 32-input pool for all arms, 27 original probe events,
five reserved audit cases and five audit opportunities. Within a regime all arms
reference the identical base snapshot, input/query schedule and audit-request
hashes. R/C/M/S retain the existing fixed policies, including lambda 0.5 and tau
0.25 where applicable.

R/C/M/S must receive the same five actual revealed findings and equivalent
verification charges in a later run. Static SAFE-Mem ignores feedback by design;
it is offered the same schedule and has the same ticket ceiling, but no consumed
audit is invented for it. The no-memory control is planned once per distinct
probed source case and shared across comparisons.

The audit requests currently contain **no verdicts**. An original attack label is
not converted into an unsafe-memory finding; a pending request is not counted as
an unresolved completed audit. Future verifier failures or uncertain outcomes
must be shared and charged consistently rather than replaced for free.

Artifacts in `public/` are sanitized **controller planning contracts**, not a
complete prompt or a streaming defense view. A later controller must expose only
currently ingested, authorized inputs and already revealed feedback at the
current cursor. Do not supply the entire future overlay/schedule to the defense.
Files in `private/` contain original case targets, cohort joins and scenario names
for the evaluator only. Those targets never update trust state.

## Cost estimate before any run

The [official OpenRouter model page](https://openrouter.ai/openai/gpt-4o-mini)
was checked on 1 November 2026: standard GPT-4o-mini rates are $0.15 per million
input tokens and $0.60 per million output tokens. The recorded observation is
[versioned separately](../configs/research/provisional_pricing_20261101.json).
Actual routing/pricing and the spending guard still require preflight before any
paid dispatch; these are planning rates, not a purchased quote.

For D00's three regimes, the exact scheduled cold-count inventory is:

| Stage | Planned count |
| --- | ---: |
| Memory answers: static plus R/C/M/S | 405 |
| Shared no-memory answers | 31 |
| Answer target judgments | 436 |
| Retrieved-entry target judgments | 255 |
| Written-entry target judgments | 20 |
| Conflict checks, working / stress assumptions | 405 / 2,430 |
| Shared pending audit jobs | 15 |
| Scheduled audit tickets per R/C/M/S policy across regimes | 15 |

Conditional cost for answer/conflict/target-judge stages is **$0.700510 working**
or **$2.291539 stress**, both including 25% headroom. The working scenario assumes
one conflict call per memory answer; stress permits six pair checks for four
served claims. Frozen output ceilings and one physical attempt per call are
used; automatic retries and cache savings are not assumed. Input-token lengths
are declared assumptions, not measured GPT token counts. The saved native prompt
envelopes are byte proxies and are not guaranteed token bounds.

**Audit-verifier inference is not priced yet and is not assumed free.** Human
labor, source-grounded QA validation, any new model/catalog work, fees, and later
robustness/scaling work are excluded. This is therefore a conditional stage
estimate, not the complete final experiment budget. Shared cache charges and
per-policy equivalent verification expense must be reported separately.

The full-context sums for all planned calls would be $29.903370 working and
$68.790660 stress. These sum deliberately conservative per-call reservations;
they are not expected charges or additional spending approvals. They demonstrate
why completion under the cap cannot be guaranteed. The guard must stop before
exceeding the remaining allowance, retaining uncertain holds.

The original shared session remains **$1.99534380 used, $0 held and $28.00465620
remaining** under the single $30 total cap. This preparation neither spends nor
creates another allowance.

## What follows without requiring human review now

1. Freeze qualified shared automated audit findings with an explicit AI basis,
   exact record/use versions and equivalent resource receipts. Do not silently
   reuse an inadequate verifier or case labels as memory ground truth.
2. Prepare a new trusted synthetic-origin state from the declared overlay,
   preserving principal ownership and ambiguous claims as unknown. The current
   store has 32 unknown external roots and 134 ambiguous claims; using it unchanged
   would not test meaningful contributor propagation. A synthetic origin is a
   controlled harness assumption, not proof of natural authorship.
3. Implement the explicitly provisional controller/transport preflight using this
   contract, then refresh the complete cost estimate. The existing scientific
   execution gate remains unchanged; this plan cannot be used to bypass it.
4. Run matched methods and save actual outputs and private judgments before
   filling a comparison table. Later human validation and a separate locked
   confirmation remain necessary for stronger research claims.

These are case-intent-controlled development inputs: 20 attack cases and 12
benign cases, equally split by domain. Their unsafe-memory balance is unknown.
They are not the protocol's validated 16-safe/16-unsafe pilot. Source-grounded
utility questions are not admitted here; original retention and restraint must
be reported separately, and low ASR alone cannot establish useful selective
transfer. Three overlays of one bag are paired sensitivity conditions, not three
independent episodes for statistical confirmation.
