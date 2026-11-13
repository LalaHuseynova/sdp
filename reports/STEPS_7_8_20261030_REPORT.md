# Steps 7–8: evidence ledger and comparison policies

30 October 2026. **Steps 7 and 8 are implemented and tested offline.** This is
software preparation, not an MPBench defense result. No genuine reviews, final
scientific pilot groups, model answers, paid requests or training were produced.
The user has deferred human validation; it was not needed for these code checks.

## What changed

All implementation is in the new
[dynamic research package](../src/ams/research/dynamic/README.md). Existing SAFE-Mem,
the dataset, the protocol, recovery outputs, provisional groups and review forms
were preserved. No old preparation or memory extraction was repeated.

| File | Work |
| --- | --- |
| [models.py](../src/ams/research/dynamic/models.py) | Immutable, allowlisted provenance, claim/chunk versions, findings, registration, audit and retraction events |
| [ledger.py](../src/ams/research/dynamic/ledger.py) | Append-only JSONL; causal prefixes; deduplicated evidence; corrections; snapshots/restart; logical, token and dollar caps |
| [policies.py](../src/ams/research/dynamic/policies.py) | Minimum-pilot R/C/M/S policies, scores, explicit gates, local safe-use exceptions and decision traces |
| [fixture.py](../src/ams/research/dynamic/fixture.py) | Shared artificial audit stream for inspecting all four policies |
| [check_dynamic_evidence.py](../scripts/check_dynamic_evidence.py) | Offline example command with a hard network guard and fresh-output requirement |
| [test_dynamic_evidence.py](../tests/test_dynamic_evidence.py) | 41 offline checks, including parametrized cases |

The package initializer exports the typed interface. Its README explains the
trust boundary and use. It is nested under `research/dynamic/`, so existing Phase 1
top-level implementation fingerprints remain valid.

## Step 7: completed behavior

- Register trusted origin metadata when records become available. Claims and
  evidence chunks use the same content-version checks. Principal-authored records
  have separate roots. Unknown/mixed attribution cannot name a guessed contributor.
- Audit findings identify actual reviewed record versions, use, policy, verifier
  and evidence references. Unsafe bundle status does not mark all its children
  unsafe. A partial safe check can preserve an exact local use without supplying
  a whole-bundle safe vote.
- Count at most one aggregate observation per independent root across claims,
  chunks, known copies, content versions and uses. An active unsafe finding takes
  precedence over safe evidence for another use. Propagated penalties never become
  new observations. Uploader identity never receives the origin's source penalty.
- Charge every new audit ticket, including unresolved results, reviews and copies.
  Retractions and corrections do not refund resources. Track physical attempts,
  native input/output tokens and integer micro-dollar amounts supplied by the
  trusted audit service. Enforce optional token/dollar limits as well as ticket caps.
- Exact duplicate event IDs are idempotent. Conflicting IDs, reused tickets, foreign
  record versions, conflicting provenance and backdated event commits fail closed.
- Correct an accusation with a new audit that supersedes the old observation, or
  invalidate it with an explicit administrative retraction. New/repaired content
  cannot silently erase the original incident. Separate, genuinely unsafe uses
  remain restricted.
- Capture immutable evidence snapshots with an exact cursor, revision and logical
  time. Decisions record those identifiers and a policy fingerprint. Later evidence
  cannot change the saved prefix. Save/load and explicit restart preserve resource
  use and do not automatically replay a later journal tail.
- Protect persistence using exclusive new-file creation, chained journal hashes,
  fsync and stale-writer rejection. Malformed or truncated journals are refused.

Only revealed audits belong in the journal. Future schedules and pending review
jobs are rejected as evidence. A snapshot's logical time is a projection cutoff,
not a wall clock: the future sequential runner must log the actual query order
and decision cursor. Snapshots cover this new ledger, not SAFE-Mem's historical
graph or conflict state.

## Step 8: completed minimum-pilot policies

The [latest protocol](MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md), Section 9, governs
these rules. Its SHA-256 remains
`5d5824e682ac58f5aabbf49be6827dca6ba0a3f6163391c1426b7562caa58c2a`.
The older proposal's weighted global/context rule was not substituted for it.

| Arm | Implemented behavior |
| --- | --- |
| R: record-only | Direct containment/recovery, zero sibling penalty |
| C: contextual reputation | Full-history contributor/context penalty |
| M: fixed multi-scope | Maximum batch, context and source penalty, with the same metadata as S |
| S: selective propagation | Maximum penalty among scopes supported by independently audited roots |

For every group, `r=(1+U)/(2+U+S)` and `d=max(0,r-0.5)`. Everyone starts with
zero reputation penalty. C/M/S use `score=cosine-0.5*d` and withhold at `d>=0.25`;
ranking-only mode is available with no hard gate. Exact rational risk arithmetic
keeps threshold comparisons stable. These summaries are not claimed calibrated.

S activates a batch after one unsafe independent root, a context after two unsafe
roots spanning two batches, and a source after four unsafe roots with at least
two roots spanning two batches in each of two contexts. Support is recomputed on
correction/retraction. The general implementation permits at least two qualifying
contexts; the two-context pilot cannot establish unseen-context generalization.

All four arms share exact local unsafe restrictions and verified-safe exceptions.
A safe exception is limited to that record/content/use/policy. Explicit trusted
ACL and original authority decisions remain binding. These inputs compose with
future retrieval; this package does not implement a general permission engine.
Candidate source context is read from registered provenance, not supplied by a
query that could choose a different reputation bucket.

Recent-four C, fixed-mixture M, broader reference defenses and adaptive auditing
remain expanded-study work. They are not represented as completed reproductions.

## Concrete artificial checks

With one unsafe root, `r=2/3` and `d=1/6`. Reviewing its known copies spends another
ticket while leaving U at one. Unreviewed same-context siblings receive a C
penalty, while S initially affects only the implicated batch. A second independent
unsafe root in another batch activates S's context scope. With two unsafe roots
and no safe roots in that context, `d=0.25`, so the hard gate applies inclusively.
An exact safe-use finding can preserve a particular sibling, subject to ACL and
authority checks; it does not clear a different confirmed unsafe record.

Other tests verify false-accusation correction against a paired correct-audit
control, scope narrowing after retraction, benign warm-up followed by compromise,
innocent relays, unknown origins, principal records, repaired content, mixed
safe/unsafe children, delayed feedback, saved decision parity after restart,
budget rejection before mutation, and journal/snapshot corruption rejection.

An inspectable fixture is saved in
[dynamic_steps7_8_fixture_v1_20261030](../research_data/dynamic_steps7_8_fixture_v1_20261030/summary.json):
nine invented roots, eighteen claim/chunk versions, five artificial tickets and
six checkpoints. Its **432 policy decisions are mechanical checks**, not benchmark
questions, model answers, human labels or attack-success observations. Every arm
uses the same snapshot and equivalent five-ticket budget. Model requests, native
tokens and actual API spending are zero. Repeating the fixture in separate temporary
directories produces byte-identical outputs, and an existing destination is refused.

## Validation and preservation

**118 relevant tests passed:** 41 new dynamic checks and 77 existing preparation,
identity, recovery and provisional checks. Targeted Ruff lint and formatting checks
passed for the new Python files.

```sh
.venv/bin/python -m pytest tests/test_mpbench_phase1.py tests/test_mpbench_identity.py tests/test_mpbench_recovery.py tests/test_mpbench_provisional.py tests/test_dynamic_evidence.py
.venv/bin/ruff check src/ams/research/dynamic scripts/check_dynamic_evidence.py tests/test_dynamic_evidence.py
.venv/bin/python scripts/prepare_mpbench_provisional.py validate --prepared research_data/mpbench_provisional_v1_20261029
```

The existing provisional validator checked all **306 payload files, 20 groups and
120 overlays**. Genuine human labels remain zero; scientific-pilot readiness is
false. This check did not regenerate or alter those groups.

A before/after SHA-256 check covered **865 pre-existing files**: source, scripts,
configuration, prompts, tests, reports, research data, local datasets and project
files. None changed. This check excludes caches, run-result directories, vendored
code, the virtual environment, bytecode and PDFs; those were not used by the new
implementation. Pre-existing working-tree changes were preserved.

Machine-readable evidence:
[validation and source/output hashes](STEPS_7_8_20261030_VALIDATION.json),
[before snapshot](STEPS_7_8_20261030_INTEGRITY_BEFORE.json),
[after check](STEPS_7_8_20261030_INTEGRITY_AFTER.json).
The repository's existing `.gitignore` excludes `tests/` and `reports/`; these new
local artifacts exist but will need deliberate inclusion if released. No commit
or staging was performed.

## What remains

**Next engineering step: Step 9, narrow SAFE-Mem retrieval integration.** Connect
trusted source/record metadata to these typed inputs, apply ACL/authority and local
safety decisions before unprivileged model exposure, cover claims and evidence
chunks, adjust ranking, refill consistently, and prove original behavior when
research effects are disabled. Preserve original prompts and explicitly reject
unsupported retrieval paths. This work is not part of this change.

Steps 4–6 still need genuine safety/provenance reviews and validated benign-use
questions before constructing the final Z-balanced pilot. Nothing here replaces
those requirements. The current provisional case-intent groups do not establish
16 safe/16 unsafe bundles. The ledger deliberately does not import their pending
audit jobs or infer safety from Y_case.

The future audit adapter must establish that supplied reviews/verifier evidence
are valid and belong to the requested ticket. The core parser rejects extra gold
fields but cannot prevent a trusted caller disguising a case label as an audit.
Runtime/evaluator isolation, real cost monitoring, integrated baseline parity,
original graph snapshots and actual safety/utility evaluation remain future work.
Journal hashes are integrity checks, not authenticated deployment provenance.

No evidence of scientific efficacy or ICML-level novelty is claimed from passing
software tests. That requires the matched-feedback, utility-preserving comparisons
and robustness studies already specified in the protocol.
