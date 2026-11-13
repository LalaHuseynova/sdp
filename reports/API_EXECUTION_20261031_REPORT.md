# Guarded API execution preparation under the USD 30 limit

31 October 2026. **The next engineering preparation is implemented and tested
offline. No paid request, model download, dependency installation, defense
evaluation, training, human annotation or final pilot generation was performed.**
Actual new API spending: **USD 0**.

The active preparation is
[dynamic_execution_prep_v2_20261031](../research_data/dynamic_execution_prep_v2_20261031/preparation_report.json).
It supersedes the interim v1 availability report; previous outputs remain intact.
Both versions reference the **same** original, unused execution session. They do
not create two spending allowances.

## Implemented

| Component | Result |
| --- | --- |
| [Execution configuration](../configs/research/dynamic_execution_v1_20261031.json) | The user's USD 30 total API ceiling supersedes the inactive USD 125 proposal; scientific settings unchanged |
| [Pricing observation](../configs/research/dynamic_pricing_20261031.json) | Official public rates rechecked on 31 October; no authenticated/provider inference request |
| [Execution session and dispatch journal](../src/ams/research/execution/session.py) | One persistent allowance, pre-dispatch reservations, exact response/billing capture, no hidden retry, fail-closed unknown outcomes |
| [Guarded sequential extension](../src/ams/research/execution/sequential.py) | Current-query answer/conflict dispatch through the shared session, durable run/session identity and checkpoint recovery |
| [Availability audit](../src/ams/research/execution/assets.py) | Recovered text/provenance/cache checks and exact candidate query catalog, with missing entries explicit |
| [Preparation CLI](../scripts/prepare_dynamic_execution.py) | Socket-blocked prepare/check commands, versioned outputs, no execution flag or key loading |
| [Integration tests](../tests/test_dynamic_execution.py) | 26 new offline checks using the real SDK and simulated HTTP responses |

Only two existing research files changed: `sequential/runner.py` gained the
explicit dispatch hook and guarded-record checks; `sequential/clients.py` gained
paid/mock/unknown accounting. Original `SequentialRun` stays offline. Original
SAFE-Mem code, model prompts, MPBench bytes, previous outputs and raw review forms
were preserved. No existing human review was overwritten.

The external controller can use this same session for original answer/entry
judgments, no-memory controls and one shared classifier preparation. Those calls
are never an implicit defense feedback source. Classifier cache misses inside an
arm, extraction misses and embedding misses still stop without an API fallback.

## USD 30 means one combined allowance

The initialized session has a **USD 30 limit, USD 0 charged and USD 0 held**.
All arms, development, controls, judges, classifier preparation and any later
smoke calls must share it. A new report or a restart does not reset it. Test
sessions are temporary simulated fixtures and do not alter this real unused
allowance. The old reproduction's separate accounting was not reused or edited.

The guard reserves funds before each physical request using the full 128k context
bound and the stage's output ceiling. Provider maximum prices, disabled plugins,
zero per-request fee and no higher-rate fallback remain enforced. SDK retries are
disabled; this version permits one physical attempt per dispatch ID, below the
protocol's maximum two-attempt allowance. Environment switches cannot silently
enable estimated billing.

Unknown billing retains its full reservation and halts all subsequent requests.
A crash after billing but before a saved reply never automatically resends the
same request. Already settled charges remain counted. Saved responses are reused
after interruption/checkpoint restore, and a run cannot switch its spending
session. Request/result hashes and SQLite checks detect unexpected changes.
Exactly-once provider billing is not claimed.

The API usage ceiling is a conditional software accounting bound. No provider key
limit was changed. Credit-purchase fees, taxes, annotation labor, local compute
and unrelated account services are outside the usage estimate; none is initiated
by this preparation.

## Updated cost position

The [official OpenRouter model page](https://openrouter.ai/openai/gpt-4o-mini/overview)
still lists **USD 0.15/M input and USD 0.60/M output**, with 128k context. The
[routing documentation](https://openrouter.ai/docs/guides/routing/provider-selection)
describes maximum-price and fallback controls used by the existing transport.

The [conditional cost estimate](../research_data/dynamic_execution_prep_v2_20261031/cost_estimate.json)
for the combined development-plus-pilot package remains **USD 13.31–14.81** using
the previous stage-length/conflict assumptions and 20% retry allowance. The
**USD 106.23 stress scenario exceeds the user's limit**. It is not an authorized
budget. The USD 30 ceiling must stop dispatch rather than permit extra spending;
completion within that ceiling is not guaranteed. The much larger full-context,
all-attempts completion calculation is separate from reserving one request at a
time.

These are planning scenarios, not measured API token use or confidence bounds.
Cached original classifiers are now confirmed for this provisional selection,
but the final selection and actual answer/conflict contexts do not exist yet.
Do not buy classifier responses for every unvalidated draft merely to fill this
availability report. Refresh the exact request inventory and disclose the final
estimate before any paid dispatch, as the user requested.

## What the read-only availability audit established

| Item | Count/status |
| --- | ---: |
| Provisional groups / distinct contributions | 20 / 640 |
| Actual recovered claims checked | 2,580 |
| Actual recovered chunks checked | 13,284 |
| Claims directly recovered | 2,580 |
| Chunks directly recovered / reconstructed and historically verified | 49 / 13,235 |
| Complete recovered-text contribution bundles | 640 |
| Exact supporting source spans checked | 21,879 |
| Existing retention/sentence/chunk-vector cache receipts verified | 5,064 |
| Available nonempty claim-vector batches | 573 |
| Distinct original-plus-draft queries checked | 1,286 |
| Cached classifier replies / query embeddings available | 640 / 640 |
| Distinct draft queries missing classifier replies / embeddings | 646 / 646 |
| Unvalidated grounded question drafts in these contributions | 877 |
| Real new-store native bindings constructed | 0 |
| Independently verified safety labels / validated questions | 0 / 0 |

The 67 contributions without a nonempty claim-vector batch have no recovered
claims; their recovered chunks do not create missing claim vectors. This says
nothing about safety or useful accessibility under the frozen external-evidence
policy. Complete text is not validated authorship, Z balance or pilot eligibility.

The [private candidate catalog](../research_data/dynamic_execution_prep_v2_20261031/private/candidate_query_catalog.json)
contains exact query requests' cached replies/embeddings, without case labels,
targets, method outcomes or future audit verdicts. It is a frozen candidate
catalog for a new study, not proof that a concurrent historical run consumed
those cache winners. Minimal historical response formats are converted using
dataclass defaults only; no text, usage, model or vector is fabricated.

The audit verifies recovered hashes and structural links, not a nonexistent
complete historical graph. Legacy IDs must not be reused as new-store bindings.
The runtime validator checks an actually supplied graph/index/binding catalog
against current policies/evidence before retrieval; genuine new-store provenance
provisioning remains required.

Classifier prompts were inspected using UTF-8 bytes plus an explicit scaffolding
proxy (2,707–2,827). These are **not measured GPT token counts or guaranteed
token bounds**. The GPT tokenizer is not locally installed and was not installed
or downloaded. Actual answer/conflict prompt sizes require the native stores and
fixed probe contexts. Billing reservations do not depend on this proxy.

## Validation

The relevant preparation/defense/budget suite passed **325 tests and 31 subtests**.
The final sequential/transport check passed **73 tests**, including all 26 new
integration checks. Targeted Ruff lint and formatting checks passed.

Checks cover cap preservation, exhausted funds before HTTP, one common allowance
across arms/controllers, exact response reuse, changed request refusal, writer
locking, lost/tampered run bindings, unknown billing/timeouts/wrong models,
environment overrides, interrupted dispatch windows, checkpoint recovery,
unfinished scientific-freeze refusal, prohibited fallbacks and oversized prompts.
All SDK/HTTP tests used `httpx.MockTransport` with sockets blocked. Their response
texts, token counts and charges are artificial test inputs, not MPBench results.

The active bundle checks **9 payload files and 454 pinned dependencies**.
Its mutable session/accounting databases are deliberately separate from frozen
preparation payloads. Previous provisional validation still checks all 306 files,
20 groups and 120 overlays. Old code-pinned checkpoints/plans remain preserved;
this code change does not bypass their original fingerprint requirements.

[Before inventory](API_EXECUTION_20261031_INTEGRITY_BEFORE.json),
[after inventory](API_EXECUTION_20261031_INTEGRITY_AFTER.json) and
[validation record](API_EXECUTION_20261031_VALIDATION.json) record preservation.
Only the two intended research integration files changed among existing files.

## Remaining work before paid pilot execution

1. Provision research-owned native stores/bindings and exact frozen write
   catalogs; retain uncertain authorship instead of assigning blame heuristically.
2. Independently validate safety/provenance and benign questions, then generate
   the final Z-balanced groups and freeze audit/probe IDs and denominators.
3. Provision the selected shared classifier catalog and missing local embeddings;
   do not regenerate different classifier responses separately for each arm.
4. Inspect actual answer/conflict prompts, refresh costs/rates and provider/account
   conditions, and prepare the scientific execution manifest. Current live
   activation explicitly refuses engineering-only/provisional plans.
5. Run the matched pilot only after those prerequisites. Budget-stopped/missing
   outcomes remain visible; arbitrary unequal truncated arm runs do not establish
   a matched safety/utility benefit.

Engineering work may continue while human review is deferred. This preparation
does not authorize an unvalidated scientific run or establish defense efficacy.
