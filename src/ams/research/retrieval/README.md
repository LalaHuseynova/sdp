# Step 9: governed SAFE-Mem retrieval

> Status note — 7 November 2026: This adapter is integrated with `sequential/`, `execution/` and `provisional_run/`. The preliminary comparison has run. This README documents the adapter and its original offline fixtures; references below to a future runner are historical. Human validation and final scientific pilot readiness remain pending. See the [current research guide](../README.md) and [project README](../../../../README.md).

This is a separate research adapter over Original `TypedStandingMemory`. Original
memory code, factories, prompts, benchmark data and previous outputs are untouched.
It supports **flat index + withhold + hops=0**, matching the reproduced path.
It does not run an experiment, create safety annotations, audit memories or answer
questions. The checked examples use invented data and exact offline responses.

## Interface

Supply a preconstructed original memory, its trusted binding catalog and one of
the [Step 8 policies](../dynamic/README.md):

```python
from ams.research.retrieval import GovernedRetrieval, RetrievalContext

reader = GovernedRetrieval(memory, bindings, policy)
context = RetrievalContext(
    evidence=ledger.snapshot(),
    access=current_access_snapshot,
    use_id=declared_use_id,
    requester="R1",  # delegated reader; separate from the task principal
    operation="read",
)
outcome = reader.retrieve_with_trace(
    session_id=store_id,
    query=query,
    k=4,
    principal="user",  # preserves original P0 task/standing semantics
    context=context,
)
original_result = outcome.retrieval
saved_trace = outcome.trace
```

`retrieve(...)` returns just the standard `RetrievalResult` when a trace is not
needed. No context is implicit or reused from an earlier request. Use one original
graph/index instance per arm: the original conflict checker can mutate contested
flags, so sharing a graph across arms would contaminate a paired comparison.

The existing answer prompt can consume `original_result.entries` and `required`
unchanged. The original MPBench `answer_fn` uses bullet-prefixed rendered entries,
`(nothing)` for an empty list, `answer_typed/v2` and its original token limit. This
adapter does not change or execute the answer/judge lifecycle.

## Trusted metadata contract

- `SourceBinding`: store-local source ID, stable artifact ID, exact content hash,
  structural role and principal ID. Repeated source display headers are never
  join keys.
- `RecordBinding`: store-local claim/chunk ID, episode-wide logical record ID,
  exact content hash, kind, actual source IDs, all applicable artifact IDs and
  explicit principal/external/ambiguous origin class.
- `BindingCatalog`: immutable bindings for currently available records/sources.
  The runtime graph, ledger registration, record versions, source roles and
  artifact policies must agree. Missing, stale or future bindings stop retrieval
  before query classification or embeddings. Logical IDs are unique across stores.
- `ArtifactGrant`: explicit readers, allowed operations and genuine copy/derivation
  parent artifacts. A record inherits the intersection of all its source/support
  artifacts and all their parents. Missing policies and inheritance cycles fail.
- `AccessSnapshot`: immutable current grants with an explicit version and content
  fingerprint. Both read permission and the requested operation are required.

The binding catalog is **trusted input**, not an authorship inference algorithm.
An original lexical `_overlap` choice alone cannot justify source-wide penalties.
For uncertain or mixed attribution, register an unknown ledger root, use an
ambiguous origin class and list all plausible policy parents. Separate principal
statements from external contributions; endorsement does not transfer ownership.
Semantic attribution and genuine review remain Step 4 requirements.

Bindings can be submitted as typed objects or imported with
`BindingCatalog.from_dict`. Import uses a strict field allowlist and rejects extra
case labels, targets or evaluator fields. This is not an operating-system sandbox;
the future runner must keep evaluator files/tools inaccessible to runtime code.

No automatic real-data binding builder is claimed here. The recovered historical
records are not a complete replayed graph. The future construction/import stage
must bind actual native IDs at ingestion from trusted preparation data, rather
than joining historical graph IDs or parsing source display labels. The test suite
includes an actual original write/extract/chunk/index pass using exact fictional
cached replies, followed by binding and research retrieval.

## Retrieval order

1. Reject unsupported/mutated configuration and invalid sidecars.
2. Use original query classification, subject logic, embedding request, cosine
   scoring and `_admits` authority checks. These query-only calls contain no
   stored records.
3. Apply current artifact permissions and shared direct record/use controls to
   **both claims and evidence chunks**. Preserve the original `external_evidence`
   restriction; a safe audit cannot override it or original standing.
4. Define a common candidate universe from originally admissible, ACL-visible
   records in cosine order. Optional claim/chunk candidate caps apply before risk
   ranking, identically across arms. Default caps are unrestricted.
5. Apply R/C/M/S decisions and rank surviving candidates with their adjusted
   scores. Refill from the same universe up to k claims and m chunks, respecting
   the original claim source cap. Evidence has its original separate slot limit.
6. Run the original conflict checker on **selected authorized claims only**, then
   reuse original claim rendering. Render selected evidence using the original
   withhold sentinel/metadata format. There is no unguarded `_evidence` fallback,
   partitioned search, confine fallback or graph expansion.
7. Return the original result type and an explicit trace: scores, reasons, pool
   membership, selected IDs, actual supplied contexts, evidence cursor/revision,
   policy/access/binding/configuration hashes and pre/post contested flags.

The trace contains controlled research metadata; it must not be appended to an
answering model's memory prompt. Only `retrieval.entries` supply those contexts.
Risk does not demote or rewrite authority, text, ownership or indexes. The original
conflict mechanism can still mark selected claims contested, as before.

### Policy-version changes

An exact safe exception is limited to its content/use/policy version. If an active
unsafe finding exists for the same content/use under an earlier policy and there
is no current safe review, every arm withholds pending recheck. The reason is
`policy_changed_recheck_required`; this does **not** create a new unsafe label or
audit vote. This common containment rule prevents an unrelated ACL update from
silently restoring a known unsafe use. A current-policy safe review may restore
that exact use while preserving the original source incident; a correction or
retraction can remove an erroneous finding.

The trusted sequential runner must supply the current access snapshot and evidence
cursor at each event, increment permission versions when policies change, and log
the actual order. The adapter cannot infer an unlogged revocation or authenticate
a caller intentionally supplying an old snapshot. Explicit older snapshots remain
usable for historical replay. No eligibility/result cache bypasses current checks.

### Static parity and source caps

`effects_enabled=False` disables audit/risk effects while keeping ACLs binding.
With all-allow policies, it preserves original selected IDs, rendered entries,
verdicts and prompt contexts, including the original source-cap underfill behavior.
The static diagnostic requires unrestricted candidate caps.

Original flat retrieval takes the cosine top-k before applying `source_cap`, which
can leave slots empty. Active R/C/M/S share full-pool refill instead, so this
selection improvement is not exclusive to S. The reproduced MPBench configuration
has `source_cap=None`, where this difference disappears. Report it explicitly if
using non-default source caps. Only the claim source cap is reused; the original
evidence path has no equivalent cap.

## Offline validation

```sh
.venv/bin/python -m pytest tests/test_dynamic_retrieval.py
.venv/bin/python scripts/check_dynamic_retrieval.py --out research_data/my_new_retrieval_fixture
```

`ExactReplayClient` returns only an explicitly supplied exact request/response pair.
A miss raises; it has no network, model download, installation or provider fallback.
The example command also blocks socket connections. A caller can supply existing
original clients to a future authorized runner; this implementation has made no
live calls and constructs no provider. Paid execution still needs the advance
cost estimate and spending bound requested by the user.

The example saves separate original/R/C/M/S graph fixtures, audit journals,
binding catalogs, access snapshots, evidence snapshots, original results and
twenty actual retrieval traces. Initial contexts match the original. Repeated
outputs are byte-identical across fresh directories; existing output is refused.
It uses `external_evidence=True` to exercise the external chunk path. Separate tests
cover the frozen `external_evidence=False` setting. The real protocol/config is
unchanged. These fixtures are not MPBench cases, independently reviewed labels,
answer evaluations or scientific evidence of safety/utility gains.

## Limits and next work

Unsupported paths fail explicitly: confine/off, non-flat indexes, hops, unsupported
source roles and populated claim derivation edges. Artifact inheritance handles
genuine supplied dependency/copy ACLs; it does not infer semantic derivation or
implement a descendant-only safety baseline.

The adapter reuses private original graph/index/formatting/conflict helpers and
duplicates the narrow withhold chunk-rendering path. Original source fingerprints
and parity tests must accompany future changes. A live cache miss can only be
prevented by choosing the offline replay client/guard; arbitrary externally supplied
live clients remain the future runner's budget/transport responsibility.

Step 10 still needs the broader sequential integration harness, original graph/index
state restart, actual response/finish-reason capture, feedback order and resource
accounting across interrupted runs. No complete historical graph reconstruction,
natural provenance authentication, human validation or pilot efficacy is established
by this adapter. The final Z-balanced pilot remains blocked on genuine reviews and
validated benign questions. Human validation can remain deferred while engineering
checks proceed offline.
