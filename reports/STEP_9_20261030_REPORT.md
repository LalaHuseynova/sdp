# Step 9: SAFE-Mem retrieval integration

30 October 2026. **Step 9 is implemented for the narrow flat/withhold/hops=0
research path.** It connects the Step 7 ledger and Step 8 R/C/M/S policies to actual
SAFE-Mem claim and evidence-chunk retrieval. All execution in this work used
invented records and exact offline responses. **Paid API cost: $0.** No MPBench
defense evaluation, training, genuine human review or final scientific pilot was run.

## Implementation

The new [research retrieval package](../src/ams/research/retrieval/README.md) wraps a
preconstructed original memory. Original SAFE-Mem code, factories and prompts were
preserved. It does not change the existing MPBench runner or silently enable a
different retrieval mode.

| Component | Behavior |
| --- | --- |
| [adapter.py](../src/ams/research/retrieval/adapter.py) | Original query classification, cosine scoring and authority; current ACL and record/use controls; R/C/M/S ranking and gating; shared refill; protected conflict calls; original result type and contexts |
| [metadata.py](../src/ams/research/retrieval/metadata.py) | Immutable native-to-logical source/record bindings, content/role/ownership checks, current artifact grants and inherited permission intersections |
| [replay.py](../src/ams/research/retrieval/replay.py) | Exact request/response replay; cache misses fail with no API/download/provider fallback |
| [fixture.py](../src/ams/research/retrieval/fixture.py) | Invented graph/index/metadata fixtures, explicitly separate from MPBench |
| [check_dynamic_retrieval.py](../scripts/check_dynamic_retrieval.py) | Inspectable offline example with socket blocking and fresh-output protection |
| [test_dynamic_retrieval.py](../tests/test_dynamic_retrieval.py) | 58 checks, including parametrized parity and failure cases |

Retrieval requires an explicit `RetrievalContext`: evidence snapshot, current
access snapshot, declared use, requester and operation. The delegated requester is
separate from the original task principal. R1 can act on P0's task without changing
SAFE-Mem's `principal="user"` semantics.

## Controls and selection

- Validate all currently available source and record bindings before query model
  calls. Missing/future records, stale content, role/ownership mismatches, missing
  policies and unregistered ledger versions stop retrieval.
- Keep episode-wide logical IDs distinct from graph-local IDs and repeated display
  headers. Do not infer culpable authorship from the original lexical source guess.
  Unknown/ambiguous origin uses an unknown ledger root and does not propagate
  contributor penalties. Principal records remain separate.
- Apply the intersection of readers/operations over every actual source artifact,
  additional trusted support artifact and supplied copy/derivation policy parent.
  Missing parent policies and cycles fail. These are explicit sidecar ACLs, not a
  general enterprise permission platform.
- Apply original `_admits`, current permissions, direct record/use controls and
  contributor penalties to both claims and chunks. A safe review cannot increase
  authority, override access denial or bypass `external_evidence=False`.
- Give all research arms the same originally admissible, ACL-visible candidate
  universe. Optional claim/chunk caps apply in original cosine order before risk
  ranking. Refill surviving candidates to the original k/m limits and preserve
  original claim source caps.
- Expose only final authorized claims to the original conflict checker. Render
  allowed claims with original `_entry` and chunks with the original withhold
  sentinel format. No separate evidence/fallback path can reintroduce exclusions.
- Return the original `RetrievalResult`, plus optional scores, reasons, candidate
  membership, chosen IDs, actual supplied contexts, configuration/binding/access
  hashes, evidence cursor/revision/time and pre/post contested flags.

An integration check found that an ACL version increment could otherwise make an
old unsafe-use finding disappear from exact-version lookup. The adapter therefore
applies a **shared containment rule across R/C/M/S**: if the same content/use has
an active unsafe finding under an earlier policy, withhold pending recheck unless
there is a current-policy safe review. This is not a new unsafe label or evidence
vote. A correction/retraction can remove an erroneous finding; a new-policy review
can restore the exact use while retaining the old genuine source incident.

The adapter does not cache eligibility or reuse a previous request context. The
future trusted runner must provide current snapshots and record the actual event
order; an intentionally supplied old snapshot is historical replay, not evidence
that an unlogged revocation was enforced.

## Original parity and source-cap behavior

With research effects disabled and all-allow access, the tested fixtures reproduce
original selected IDs, entries/metadata, verdicts, conflict requests, contested
flags and rendered answer-prompt contexts. Sixteen combinations cover k in
{0,1,4,20}, conflicts enabled/disabled and external evidence enabled/disabled under
the reproduced `source_cap=None` setting. A separate source-cap fixture checks
the original top-k-before-cap underfill behavior at k=4.

Active R/C/M/S all refill from the full common universe. Original flat retrieval
can underfill when `source_cap` is non-null because it caps only after taking the
top-k. Static parity mode preserves that behavior; active research arms share the
same refill change. The frozen MPBench configuration has `source_cap=None`, so
this distinction does not affect the planned default experiment. Non-default
source-cap studies must disclose it. The original evidence path has no source cap.

Original prompts and the 200-token answer setting were not edited. The tests check
the original answer-prompt format, including bullet-prefixed sentinel entries and
`(nothing)` for an empty list, without calling an answering model.

## Validation and example artifacts

**176 relevant tests passed:** 118 earlier preparation/ledger/policy checks and
58 new retrieval checks. Targeted Ruff lint and formatting checks also passed.

The new checks cover:

- Original behavior and byte-identical contexts with effects disabled.
- An actual original write/extraction/chunk/index pass using exact fictional
  responses, followed by binding and integrated retrieval.
- Claim/chunk exclusion before conflict exposure, bounded refill, source caps and
  common candidate universes across arms.
- Current-policy denial on repeated queries and unchanged embedding-cache keys;
  operation denial, multi-parent chunks and inherited artifact restrictions.
- Safe-use exceptions, false-accusation correction, older evidence snapshots and
  policy-version recheck, without changing evidence counts or refunding audits.
- Conservative attribution and original authority/external-evidence restrictions.
- Missing/stale metadata and unsupported paths failing before model calls.
- Exact replay misses, repeatable example output and refusal to overwrite outputs.

The [offline example summary](../research_data/dynamic_retrieval_fixture_v1_20261030/summary.json)
contains **20 retrieval checks**, four arms and five stages: initial, one incident,
two incidents, correction and revocation. Each arm has its own original graph and
identical shared audit stream; each consumes three artificial tickets. Initial
results match the original. Journals, binding catalogs, access snapshots, evidence
snapshots, original results and complete retrieval traces are saved in that new
directory. Repeating the command in fresh directories produces identical bytes.

The example deliberately enables external evidence to exercise that path. Separate
tests cover the frozen external-evidence-off setting. These are ten invented roots
and twenty records per arm, not newly annotated MPBench contributions. The twenty
checks are not an ASR/utility estimate or a pilot substitute.

```sh
.venv/bin/python -m pytest tests/test_mpbench_phase1.py tests/test_mpbench_identity.py tests/test_mpbench_recovery.py tests/test_mpbench_provisional.py tests/test_dynamic_evidence.py tests/test_dynamic_retrieval.py
.venv/bin/ruff check src/ams/research/retrieval scripts/check_dynamic_retrieval.py tests/test_dynamic_retrieval.py
.venv/bin/python scripts/check_dynamic_retrieval.py --out research_data/my_fresh_retrieval_fixture
```

## Preservation and remaining work

Before/after hashes show **887 pre-existing files unchanged**, including Original
SAFE-Mem, Step 7–8 code, official data, prompts, previous reports and research
outputs. Pre-existing working-tree edits were preserved. Caches, old run-result
directories, vendor code, environments, bytecode and PDFs were outside the hash
inventory and were not used for this implementation.

The prior provisional validator still passes all **306 payload files, 20 groups
and 120 overlays**. Genuine human labels remain zero and scientific-pilot readiness
is false. No old recovery, extraction, group generation or annotation work was
repeated. The protocol/configuration and original source-pool contents are unchanged.

[Machine-readable validation and hashes](STEP_9_20261030_VALIDATION.json),
[before inventory](STEP_9_20261030_INTEGRITY_BEFORE.json),
[after check](STEP_9_20261030_INTEGRITY_AFTER.json).
The repository currently ignores tests/reports; no staging or commit was performed.

**Next engineering work is Step 10:** strengthen the sequential integration harness
and validate graph/index state restart, real response/finish-reason capture, event
ordering, failure handling and complete resource accounting across interruptions.
The current trace does not constitute a full historical SAFE-Mem graph snapshot.

Actual MPBench use additionally requires trusted native-ID bindings at construction
or a validated graph import; a complete historical graph was not fabricated from
the recovered text records. The catalog validates structural consistency, not
semantic attribution or human review authenticity. Confine/off, non-flat indexes,
graph hops, unsupported source roles and populated claim derivation edges fail
explicitly. A descendant-only safety baseline remains separate work.

Human safety/provenance and benign-question reviews remain deferred. They are still
required for the final Z-balanced scientific pilot. No efficacy, verifier accuracy
or ICML novelty claim follows from the software checks. No paid calls were needed;
future paid execution must receive the advance estimate and spending bound already
requested by the user.
