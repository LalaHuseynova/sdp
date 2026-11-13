# Steps 7 and 8: offline evidence and policy mechanics

> Status note — 7 November 2026: The ledger/policy package is complete for the minimum version. Retrieval and sequential integration now exist in `retrieval/` and `sequential/`; guarded execution and the preliminary comparison also ran. Statements below about what this package does not do describe its module boundary, not unfinished project-wide integration. `verified_audits` is an interface mode, not proof of human validation; the executed provisional study used saved AI assessments. See the [current research guide](../README.md) and [project README](../../../../README.md).

This package implements the minimum-pilot rules in Section 9 of
[the experimental protocol](../../../../reports/MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md).
It does not load MPBench, generate annotations, call a model, retrieve memories,
or run an answer-level experiment. All example findings are explicitly artificial.
Existing Phase 1, recovery and provisional materials are unchanged.

## Evidence lifecycle

1. Create an `EvidenceLedger` in a fresh file with an episode ID and audit limit.
   The default `verified_audits` mode refuses artificial evidence. Use
   `artificial_fixture` mode only for software checks.
2. At ingestion, append a `Register` event with trusted `Provenance` and claim/chunk
   `StoredRecord` versions. Principal statements use a separate principal root.
   Unknown or mixed attribution has no contributor ID. Known copies share an
   independent root; identical text alone does not establish that relationship.
   Context and batch belong to that origin, rather than the current query.
3. A trusted audit adapter supplies `Audit` events ONLY when findings are revealed.
   Each event names a unique ticket, root, use, policy version, verifier, evidence
   references and content versions. Findings identify the actually reviewed
   claims/chunks. Unsafe bundle status does not label every other child unsafe.
4. Take an immutable `snapshot(as_of=logical_time, cursor=committed_cursor)` and
   apply `Policy("R"/"C"/"M"/"S").decide(candidate, snapshot)`. Each decision
   records the exact evidence revision/cursor/time and policy fingerprint.
5. Append corrections with a new ticket and `supersedes=old_event_id`. They must
   review the original content/use/policy, rather than hiding an incident through
   repaired content. A `Retract` event can invalidate an active audit without
   creating a safe vote. Superseded evidence is never implicitly revived.
6. Save a snapshot to a new path. Loading it reconstructs exactly its prefix;
   `EvidenceLedger.restore(snapshot, new_journal)` explicitly creates a new journal
   at that prefix, retaining all consumed tickets. It never replays a later tail.
   The snapshot retains `as_of`; pass that time explicitly when reproducing a
   decision whose time was later than the last evidence event.

Event commits are single-writer, append-only and nondecreasing in reveal time.
Readers must record both cursor and time: a time alone is insufficient if several
commits share that time. `snapshot(as_of=...)` is a projection, not a scheduler or
wall-clock advance. The future sequential runner must enforce query/ingest/reveal
order and store the decision cursor; this package cannot infer unlogged queries.
Pending jobs and future audit schedules do not belong in a runtime snapshot.

Exact duplicate event IDs are idempotent; conflicting reuse fails. Ticket reuse
is rejected. Different tickets spent on the same root still cost additional
audits, including unresolved results and copies, but cannot multiply its evidence
vote. Tokens, physical attempts and integer micro-dollar costs are recorded;
optional token/dollar caps apply in addition to the logical ticket cap. No refund
occurs on correction or retraction. Actual experiment-wide shared-cache charges
will require a separate accounting view in the future experiment runner.

A safe bundle vote requires nonempty, complete review of **all registered record
versions under that root**, including known copies/old versions if present. This
is deliberately conservative. Partial safe findings use an unresolved bundle
outcome: they can preserve exact local uses without claiming a fully safe bundle.
This extra validation does not create an independently verified label; the audit
adapter must supply real evidence. A later adapter can register separate versioned
bundle manifests if more precise whole-bundle accounting is needed.

## Four policies

All share direct unsafe-record containment, exact safe-use exceptions, correction
semantics, and external hard permission/authority checks. The candidate provides
explicit trusted ACL and original SAFE-Mem authority booleans. These are necessary
composition inputs, not a new ACL engine. Permission or authority denial always
wins. Local findings apply only to the exact record/content/use/policy; repairs
can restore the new version while the original genuine source incident persists.

One independent root contributes at most one aggregate observation across active
audits, uses and content versions: unsafe takes precedence over safe; unresolved
adds neither. Unknown attribution and principal roots affect local records only.
The uploader is never substituted for the attributable origin.

For every group, `r=(1+U)/(2+U+S)` and `d=max(0,r-0.5)`:

| Arm | Penalty on uninspected records |
| --- | --- |
| R | Zero; direct record/use containment only |
| C | Contributor/context `d`, full history |
| M | Maximum of batch, contributor/context and contributor `d` |
| S | Maximum over currently supported scopes |

S supports a batch after one unsafe root; a context after two unsafe roots spanning
two batches; and a contributor after four unsafe roots, with at least two roots
spanning two batches in each of two contexts. Support is recomputed after evidence
correction. In the two-context/two-batch pilot these are the exact frozen gates.
The general implementation requires at least two qualifying contexts; testing
transfer into an unseen context remains future research.

C/M/S default to `score = cosine - 0.5*d` and withholding at `d >= 0.25`.
`threshold=None` provides the specified ranking-only variant. R always uses zero
weight and no reputation gate. Exact rational risk arithmetic avoids boundary
rounding at the inclusive gate. These are heuristic summaries, not calibrated
probabilities. Policy decisions never become new evidence.

Only the minimum-pilot full-history C and maximum M are implemented. Recent-four
C, fixed-mixture M, other reference defenses, adaptive audit allocation and
descendant containment remain expanded-study work. Claim/chunk eligibility,
SAFE-Mem conflicts, refill, original answer prompts and final candidate selection
are **Step 9**, which is not integrated here.

## Run offline checks

Use the existing environment; no install, download or API key is required:

```sh
.venv/bin/python -m pytest tests/test_dynamic_evidence.py
.venv/bin/python scripts/check_dynamic_evidence.py --out research_data/my_new_fixture
```

The example uses nine invented contributions, eighteen record versions and five
shared artificial tickets. It writes an append-only journal, snapshots, and the
four arms' decisions at each stage. These are software mechanics, not ASR or benign
utility results, and create no human annotations or final pilot groups.

## Trust boundary and limits

Only the trusted harness may register provenance, reveal audit findings or retract
evidence. The API does not authenticate people or verify that a supplied human
review actually occurred. An independently validated annotation/audit adapter is
still required before using the real pilot. The parser rejects extra fields such
as case labels or target answers; it cannot detect a caller that disguises a gold
label as an audit. Runtime/evaluator process isolation remains a runner requirement.

The journal has schema checks, chained hashes, exclusive creation and stale-writer
rejection. It refuses malformed/truncated files; there is no silent repair or
automatic overwrite. Hashes detect accidental corruption, not malicious rewriting
by a host with access to all files. Snapshots cover this ledger, not the historical
SAFE-Mem graph or original conflict state. No claims about scientific efficacy,
real verifier accuracy, task utility or paper acceptance follow from these checks.
