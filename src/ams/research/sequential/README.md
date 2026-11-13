# Step 10: offline sequential execution and restart

> Status note — 7 November 2026: This remains the offline execution/restart layer. The separate `execution/` package supplies guarded paid calls, and `provisional_run/` uses the integrated path. The preliminary comparison completed; that does not imply a completed human-validated pilot. See the [current research guide](../README.md) and [project README](../../../../README.md).

This package runs one explicitly dispatched research action at a time over the
[Step 9 adapter](../retrieval/README.md). It supports exact offline replay clients
only. It does not instantiate a provider, download models, execute MPBench,
generate safety labels, train a model or redeem a paid audit.

## Public interface

```python
from pathlib import Path
from ams.research.sequential import RuntimeState, SequentialRun, Step

# Use a research-owned original memory with unused ExactReplayClient instances.
initial = RuntimeState.create(
    memory,
    bindings,
    access,
    evidence_snapshot,
    policy,
    writers=("user", "contributor_1", "contributor_2"),
)
with SequentialRun.create(Path("my_new_run"), initial) as run:
    result = run.step(
        Step.query(
            "query_001",
            10,
            session_id=store_id,
            query=query,
            use_id=use_id,
            requester="user",
            principal="user",
            k=4,
            answer=True,
        )
    )
    run.checkpoint(Path("my_new_checkpoint"))

with SequentialRun.restore(Path("my_new_checkpoint"), Path("my_new_resumed_run")) as run:
    run.recover()  # finishes a pending action if the checkpoint contains one
    # Dispatch the next action only when it actually becomes available.
```

`SequentialRun(existing_directory)` opens an interrupted run in place. Opening
restores state but makes no model call; pending execution is explicit with
`recover()`. An existing destination is never overwritten. Checkpoints remain
fixed even when their original source run later advances.

`RuntimeState.create` replaces the supplied memory's clients with offline recorded
clients. Supply a separate graph/index instance per arm. Native source, artifact,
claim and chunk bindings are still trusted inputs; the engine cannot invent valid
authorship or independent reviews. Previously used unrecorded clients are refused,
because their actual historical responses cannot be recovered by guessing a cache
winner. No SDK object, credential or executable callback is serialized.

## Actions and causal order

| Kind | Work |
| --- | --- |
| `query` | Current bindings/ACL/evidence through R/C/M/S retrieval; optional original typed answering prompt, temperature 0 and 200-token limit |
| `reveal` | One currently revealed Audit or Retract event; the original incident/accounting rules remain binding |
| `policy` | An explicit new permission version; old versions cannot silently be reused |
| `write` | Authorized original SAFE-Mem write using frozen responses, then trusted new bindings, access grants and provenance registrations |
| `draw` | An explicit seeded RNG draw, for checking future audit/probe allocation state |

Use `Step.query(...)`, `Step.reveal(...)`, or `Step.make(id, time, kind, payload)`.
Only allowlisted fields are accepted. No entire future schedule, raw case object,
expected-memory field or evaluator result is accepted. Future audit outcomes belong
to the external trusted controller and enter only at their reveal event. Frozen
extraction/answer tables are privileged offline replay data, not feedback state.
Answer results never become safe/unsafe source observations.

Times cannot go backwards after any committed query or event. Equal-time actions
remain ordered by the committed cursor. The runner supplies its current access
and evidence snapshots; queries cannot inject older snapshots. Retrying the same
action ID/payload returns its saved result without executing again; conflicting
ID reuse fails. Dispatching another action while one is pending is refused.

For writes, `writer` must be in the trusted initial writer policy. The write's
`user_query` is the trusted task principal's input, not an authentication mechanism
for an external uploader. Bindings must extend the old catalog, and existing graph
nodes/chunks cannot be overwritten. New isolated artifact grants can extend the
current version if all old grants are unchanged; changing old permissions requires
a fresh version. Registrations carry provenance only, never safety labels. These
checks do not replace the annotation/authentication boundary from earlier phases.

## What is checkpointed

- Original graph claims, sources, entities, source/entity lookup lists, sentence
  next/previous links, contested flags, order and the shared next-ID counter.
- Claim/chunk vector rows and ID order; matrices rebuild deterministically.
  Evidence chunks, their original parents and entity-name vector indexes.
- Original memory settings/counters; FixedUse or original UseTypeClassifier,
  including its cached query rungs/subjects and unparsed counter.
- Client and prompt-library sharing relationships, exact response tables, captured
  requests/responses/errors, used prompt fingerprints and all prompt-file hashes.
- Binding catalog, inherited access policy, seen policy versions, revealed
  evidence prefix, audit budget, R/C/M/S settings, logical clock and RNG state.
- Saved results, selected contexts, answer text, cached/provider metadata, native
  reported usage and raw finish reasons. A `length` finish is preserved and flagged.

State uses explicit JSON types rather than pickle or dynamic class imports.
Only flat/withhold/hops=0 and the supported original classifier/client types are
accepted. Partitioned state cannot be silently omitted. Code hashes, Python,
machine/byte order, NumPy and SQLite versions, and prompt-file hashes are checked
on restore. Checkpoints target the same validated environment/workspace; portable
migrations are separate work. The codec reconstructs these new research states,
not an unavailable complete historical SAFE-Mem reproduction graph.

## Persistence, failures and resource counts

A single-writer SQLite journal stores append-only **intent**, **completed call**
and **commit** rows. Call responses are durably saved before consumption. Each
commit atomically stores its result and complete runtime state. Hash chains,
SQLite integrity checks, source fingerprints and a checkpoint database checksum
detect unexpected changes. Locks prevent two writers. No stale state is merged.

If execution stops between a saved call and a commit, recovery starts at the last
committed state and replays the exact saved call prefix. An unexpected request or
unused saved call stops recovery. A saved reply wins over any later response-table
value. Already captured calls are neither requested nor counted again.

Ordinary execution failures produce `status="failed"`. Graph, indexes, ACLs, RNG
and classifier changes roll back; attempted-call histories remain. Partial
retrieval contexts and the literal error are saved. Failures are not successful
defense outcomes and must remain in later coverage/denominator accounting.

`run.state.usage()` describes committed state. `run.resources()` additionally
reports durable inference calls from a pending action. Reported input/output
tokens and equivalent cost sum the captured response metadata; missing-response
usage remains explicitly unknown. Audit tickets/attempts/tokens/cost are tracked
separately from query/extraction/conflict/answer replay to avoid double counting.
Actual paid cost and live API calls are zero for this offline engine.

These checks establish offline replay behavior, not exactly-once live API billing.
A live request could complete before a response was saved; that unknown-outcome
case needs a separate provider/accounting integration before paid execution. API
latency is not measured by replay. Audit redemption must also be controlled before
feedback is supplied; this runner is not an adaptive verifier service.

Full state is stored at each commit for simplicity. This is appropriate for
correctness checks and small pilots, not a storage/throughput claim for full MPBench.
Incremental snapshots, live transport, evaluator isolation and hardware/power-loss
reliability need separate validation. Hashes are not signatures against a host
that can rewrite all files; restore only trusted checkpoints.

## Reproduce the offline checks

```sh
.venv/bin/python -m pytest tests/test_dynamic_sequential.py
.venv/bin/python scripts/check_dynamic_sequence.py --out research_data/my_new_sequence_fixture
```

The example has four separate R/C/M/S states. It compares uninterrupted execution,
an older checkpoint whose source subsequently advances, and resumed execution.
Each trajectory has twelve events: six completed query checks, one intentionally
failed cache-miss query, plus feedback, correction, permissions, RNG and write
events. Outputs, graph/index state and accounting must match. These are invented
records with artificial response usage, not MPBench results, human validation or
a real API-cost estimate. Original data, prompts and previous outputs stay intact.
