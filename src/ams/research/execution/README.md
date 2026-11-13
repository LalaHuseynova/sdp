# Guarded API execution preparation

> Status note — 7 November 2026: Guarded execution was subsequently used for the preliminary comparison through `provisional_run/`. The local research ledger was rechecked at USD 2.09412345 spent, with zero holds. This is separate from original-reproduction accounting. The final human-validated pilot remains pending. See the [current research guide](../README.md) and [project README](../../../../README.md).

31 October 2026. This package connects the sequential research engine to a
durable OpenRouter dispatch journal and the existing `BudgetGuard`. It makes no
request on import, preparation, opening a session, restoring a run or reading a
checkpoint. No API credential is loaded by the preparation CLI.

The user's **USD 30 total API limit** supersedes Step 11's inactive USD 125
proposal. It covers the combined development/pilot package, including controls,
classifier preparation, judgments and any later smoke calls. It is not a separate
allowance for each arm, process, report version or restart. No credit purchase,
tax payment or other provider service is initiated.

## Offline preparation

```sh
.venv/bin/python scripts/prepare_dynamic_execution.py prepare --out research_data/my_new_execution_preparation
.venv/bin/python scripts/prepare_dynamic_execution.py check --bundle research_data/my_new_execution_preparation
.venv/bin/python -m pytest tests/test_dynamic_execution.py
```

The CLI blocks sockets, refuses existing output destinations and has no execution
switch. It validates previous preparation/recovery outputs, checks the current
human-review forms, audits the 640 provisional source contributions, and creates
an aggregate availability report and a private exact-query response catalog.
No final Z-balanced pilot group, review, answer or target-judge result is created.

All report versions use the same initialized allowance at
`research_data/dynamic_execution_prep_v1_20261031/session`. A new report never
resets it. The session is separate from the original reproduction's accounting.
Source/prompt/review dependencies are pinned in each new preparation manifest.
Previous planning outputs remain intact; changed research code needs a new
engineering version rather than bypassing old fingerprint checks.

## Budget and dispatch semantics

`ExecutionSession` uses one SQLite allowance fixed at USD 30. The existing guard
reserves full 128,000-token input context and the exact output ceiling before each
physical request. GPT-4o-mini, official HTTPS OpenRouter, maximum prices of USD
0.15/M input and USD 0.60/M output, zero per-request fee, disabled plugins and no
higher-rate fallback remain enforced. The reservation is independent of prompt
size estimates. This is a conditional software bound on routed API usage, not a
guarantee about unrelated account services or provider violations.

Hidden SDK retries are disabled. This version performs **one physical attempt
per dispatch ID**, below the protocol's maximum of two. A saved completed reply
is returned on redispatch of that identical ID/request. Changed request reuse is
refused. Failure does not become a model refusal or successful defense outcome.

An intent is persisted before sending. Native usage, generation/billing receipt,
exact reply and finish reason are recorded on return. Unverified billing retains
its full hold and stops all subsequent dispatch. A crash before saving a reply
leaves an unresolved dispatch which is never automatically sent again. A charge
that was already authoritatively settled remains charged even if the reply was
lost. Human/account reconciliation, not restarting or guessed zero usage, is
needed to handle those cases. Exactly-once provider billing is not claimed.

The dispatch journal uses a single-writer lock. Request/result hashes and the
existing accounting audit detect unexpected changes. Mock and live accounting
cannot share a session. Test-only `arm_mock` accepts `httpx.MockTransport`
exactly; it cannot contact a real endpoint. Simulated charges are labeled and
never reported as actual paid spending.

## Runner integration

`GuardedSequentialRun` extends the original offline `SequentialRun` through one
explicit lookup hook. `SequentialRun` itself stays offline. Attach an already
opened shared session before the first action. It is not reconstructed from a
serialized SDK or callback.

Only answer/conflict calls from a currently dispatched **query** can use the
session. Writes and embeddings remain exact offline replay; query classification
must use the common frozen response catalog. A classifier miss cannot issue a
different API request separately for each arm. An external controller can use
the same session for no-memory answers and original judgments, or explicitly
prepare a classifier response once through `complete_shared_classifier`.
Evaluation results never enter source evidence automatically.

The run/session ID is pinned inside the run database and copied with checkpoints.
An external sidecar is checked against that binding; losing it does not generate
a new dispatch identity. Restoring an old checkpoint retains the original session
and exact dispatch IDs. Responses captured in either journal are reused.

`run.resources()` retains its deterministic per-run accounting. Additional
`run.execution_resources()` includes the current shared allowance. That allowance
is never rolled back by restoring an earlier graph checkpoint. Unknown paid
attempts remain explicit rather than being assigned zero cost.

## Availability and scientific boundaries

The availability audit checks actual recovered claim/chunk hashes, contribution
membership, exact supporting spans, saved cache receipts, claim-vector batches,
and exact classifier/query-embedding requests. Historical cache responses omit
some response-dataclass defaults; conversion adds only those defaults and marks
the new lookup as cached. Missing text, vectors, usage or model are not invented.

The exported classifier catalog is a frozen **candidate for a new study**, not
proof that a concurrent historical run used that response. Historical source and
claim IDs are not new-store bindings. `validate_runtime_assets(state)` validates
an actually supplied graph/index/binding catalog at its current event cursor; it
does not infer authorship, human agreement or complete historical graph state.

Prompt checks report UTF-8 bytes and a reproducible conservative byte proxy with
scaffolding. They do **not** claim measured GPT token counts or a guaranteed
tokenization bound. Native answer/conflict prompt sizes remain unavailable until
real native stores and probe contexts are provisioned. No tokenizer/model is
downloaded and no dependency is installed.

Live activation calls the scientific-freeze gate before constructing a provider.
The current gate intentionally rejects every engineering-only/provisional plan.
It has not been replaced by a caller-provided `ready=True`. A future scientific
manifest promotion, current rates/account preflight, actual native stores,
fixed audit/probe IDs and independently reviewed labels/questions are still
required. The current CLI therefore cannot launch a paid or scientific pilot.

The existing conditional development-plus-pilot estimate remains USD
13.31–14.81 at the observed rates. The larger stress scenario exceeds USD 30.
The new ceiling stops work; it does not promise completion. Budget-stopped or
missing outcomes must remain visible in paired coverage and denominators.
Paired block scheduling belongs to the eventual pilot controller; arbitrary
truncated arm runs must not be reported as a matched scientific comparison.
