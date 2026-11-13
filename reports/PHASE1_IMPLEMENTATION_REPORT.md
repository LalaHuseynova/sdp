# Dynamic provenance defense: Phase 1 implementation report

28 October 2026. **Offline preparation implemented and validated. The real 32-case
pilot is not ready.** No new model inference, SAFE-Mem evaluation, training, paid
API call, dependency installation, dynamic trust update or selective propagation
was performed. Artificial strings in unit tests are fixtures, not annotated MPBench.

The primary reference remains [MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md](MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md),
SHA-256 `5d5824e682ac58f5aabbf49be6827dca6ba0a3f6163391c1426b7562caa58c2a`.
The extended proposal, implementation roadmap and first-experiment document were
reviewed for context. Their older four-contributor pilot is superseded by the
latest two-contributor, two-context, 32-case design. None of those documents changed.

## Implemented scope

- Strict read-only decoding and hashing of the official files, including the
  concatenated JSON objects that a line-only loader could miss. Original IDs and
  labels remain in the evaluator view; split-qualified keys prevent collisions.
- Stable logical contribution/artifact/claim IDs; exact original source boundaries
  and character offsets; principal turns remain separate from external artifacts.
  Saved heuristic source IDs are diagnostic only. Actual claim-origin/span mappings
  require independent review; author names inside text are not trusted identity.
- Blinded annotation packets from real saved claims, independent-review forms,
  disagreement/adjudication checks, grounded utility-question forms, and guarded
  eligibility. Empty and uncertain bundles do not become safe; an adversarial case
  can have a different record/use label without changing its official case label.
- Duplicate/template components, conservative group-disjoint sampling, exact
  per-domain strata, fixed development/locked bag partition, and seeded ordering.
- An exact integer dynamic-programming sampler for the protocol's product-weight
  subset distribution, including exact `2.25 = 9/4` weights. All six strong/weak/null
  source/batch correlation cells are available. Assignment does not rejection-sample
  contributors into identical risk rates or force every realized group to be mixed.
- Two contributors, two contexts, two batches per contributor/context, four independent
  contributions per batch. Primary permissions are all-allow; the separate policy
  plan selects restricted and write-denied quarters independently of labels.
- Shared core audit schedules at B=1/3/5 with the same five reserved contributions
  and 27 original probes; a fixed-audit-ID control; grounded-question ordering;
  equal R/C/M/S input/event digests and exact per-cohort query denominators.
- Auxiliary reviewed-input recipes for nine-audit compromise; five-audit false
  accusation/correction and its matched correct-audit control; declared copies with
  one observation root; the prescribed frozen noise channel and 0/4/16-query delay.
  No real auxiliary pools were generated. False accusation requires 16 extra reviewed
  reserve cases, separate from the main 32-case bags.
- Explicit public schema allowlists, private gold/schedule files, prefix-only runtime
  views, and permission-version view checks. Future audit results never enter a
  projected earlier view. Final episode metadata IDs use a private HMAC key so the
  public master seed cannot enumerate bag/profile names from unkeyed IDs.

The builder produces preparation artifacts only. It does not implement any R/C/M/S
decision policy, classify query outcomes, invoke a verifier, or run an experiment.

## Actual dataset composition

| Existing input inventory | Count |
|---|---:|
| All source cases | 6,240 |
| Attack / benign input cases | 3,241 / 2,999 |
| Readable questions | 5,996 |
| Readable attack / benign questions | 2,999 / 2,997 |
| Original explicit-retention / restraint targets | 249 / 2,607 |
| Readable benign cases without a scored target | 141 |
| Write-only cases preserved in inventory | 244 |
| Saved claims imported for inspection | 22,089 |
| All-input cases with no saved claim | 1,271 |

The review-candidate inventory includes readable email/file cases with a nonempty
original target. Counts below are **official input labels, not verified memory labels**.

| Context | Attack cases | Explicit benign | Suggestive benign | Review candidates |
|---|---:|---:|---:|---:|
| Email | 549 | 39 | 473 | 1,061 |
| File/document | 551 | 36 | 466 | 1,053 |
| Total | 1,100 | 75 | 939 | 2,114 |

Those 2,114 packets contain 8,544 saved claims. Of the packets, 1,873 have at least
one saved claim and 241 are empty. Nonempty claims alone do not establish either
external attribution or safety. Across the whole input pool, grouping found 5,058
components, including 469 multi-case components and three oversized components
of 184, 44 and 36 cases needing manual review. Raw counts permit the nominal
quotas, but independent complete memory/use annotation capacity is unestablished.

The **planned**, ungenerated bag has 16 email and 16 file/document cases:

| Stratum per context | Required per bag | Required across 20 bags |
|---|---:|---:|
| Attack input, independently unsafe memory bundle | 8 | 160 |
| Attack input, independently safe memory bundle | 2 | 40 |
| Explicit benign, safe memory bundle | 1 | 20 |
| Suggestive benign, safe memory bundle | 5 | 100 |

Thus the declared balance is **16 unsafe / 16 safe memory bundles**, while original
input labels are **20 attack / 12 benign**. The latter are not forced to 50/50.
Contributor/context/batch risk fractions vary with the controlled distribution;
realized counts are recorded, including rare pure groups. There is no resampling
based on defense performance or desired contributor rates.

## Current readiness and missing inputs

**Real episodes generated: 0. Independently reviewed Z bundles: 0. Verified
claim-origin maps: 0. Validated source-grounded questions: 0.**

The current extraction journal saved claims but did not serialize evidence-chunk
texts and their source mappings. These chunks participate in the unchanged m=4
retrieval path. Claim-only reviews therefore cannot certify the complete memory
bundles required by the protocol. Current exports are preparatory packets; final
annotation should use the actual full record set.

`prepare --evidence-catalog` supports importing an actual complete frozen/cached
chunk export with source-payload hashes, actual text hashes, unique IDs, completeness
and exporter/configuration provenance. Its checks do not prove the exporter honest;
the trusted preparer must establish that it captured the actual original chunks.
No such export exists here, and no boundaries/texts were guessed. Importing chunks
changes packet hashes and requires review of the resulting full packets.

The remaining requirements are:

1. Obtain genuine frozen/cached evidence chunks and verified source mappings, then
   regenerate complete packets without model calls or fabricated replacement text.
   If reconstruction needs work beyond available offline records, specify it before
   attempting it; this report makes no spending authorization.
2. Two independent human reviews of actual records and intended uses; a third
   reviewer resolves disagreement. Record evidence, uncertainty and provenance.
3. Human-authored, independently validated source-grounded questions for every
   selected safe contribution, with actual reference spans and answer aliases.
4. Review duplicate/generic components and satisfy all strata with group separation.
   In particular, the required 40 safe adversarial memory bundles per domain might
   not exist after complete chunk/use review. Do not silently substitute other cases.
5. Freeze proposed bags and perform the final uniqueness/disambiguation review of
   utility support in each exact 32-case pool. Stale/missing selection hashes block release.

`build-pilot` currently exits **2** with the expected diagnostic:

```text
Bag 00 email/attack/unsafe: needs 8, has 0 group-disjoint reviewed candidates; no fallback
```

It writes only a [not-ready report](../research_data/pilot_build_00/readiness_report.json).
It creates no real episode files. Even sufficient claim-only reviews would hit the
separate missing-chunk gate rather than mark the m=4 pilot ready.

## Offline verification

| Check | Result |
|---|---|
| New Phase 1 tests | 30 passed |
| Existing MPBench identity tests | 5 passed |
| Targeted Ruff checks | Passed |
| Actual preparation validation | All 6,240 inputs checked; source spans/schema/hashes passed |
| Preparation replay | All 13 generated files byte-identical with the recorded identifier key |
| Blinded exports | Two blank reviewer exports; identical packets, no case index/peer votes |
| Filesystem modes | Private files 0600, private directories 0700 |
| Missing-annotation and missing-chunk guards | Blocked release as intended |
| Pre-existing protected files | 270 unchanged; zero changed files |

Tests cover strict parsing, source offsets, duplicate components, independent review,
adjudication, actual claim/use versus case labels, invalid/empty bundles, utility
support, exact subset normalization/transition probabilities, deterministic assignments,
balance, common roots/orders, fixed-ID controls, unchanged probe cohorts across budgets,
shared-arm digests, schema leakage, keyed IDs, detached prefix views, revocation,
compromise, false accusation/correction, copies, noise and delay. No test calls a model.

Commands used:

```sh
PYTHONPATH=src .venv/bin/python -m pytest -o addopts='' \
  tests/test_mpbench_phase1.py tests/test_mpbench_identity.py -q
.venv/bin/ruff check src/ams/research scripts/prepare_mpbench_phase1.py \
  tests/test_mpbench_phase1.py
PYTHONPATH=src .venv/bin/python scripts/prepare_mpbench_phase1.py validate \
  --prepared research_data/mpbench_phase1
```

Machine-readable evidence:
[validation results](PHASE1_VALIDATION_RESULTS.json),
[replay check](PHASE1_REPLAY_CHECK.json),
[before fingerprints](PHASE1_INTEGRITY_BEFORE.json),
[after integrity check](PHASE1_INTEGRITY_AFTER.json).

## Preserved original files

All 270 pre-existing source/script/config/prompt/test/data/project and required
research-document fingerprints match their before state. The before/after canonical
aggregate is `1009e256fccc923cbe95410c9f741d0f97b674cc55dc5a3ae969d76144e08676`.
Pre-existing working-tree edits were preserved; they were not reverted or attributed
to this Phase 1 work.

Official raw SHA-256 values remain:

```text
adversarial_data.jsonl.jsonl
f2d23a5a2d483889eb2fdd9a2a082f0759603bc0a17664814a7caafbd318f90d
benign_data.jsonl.jsonl
707ef7e311e147d9818a8a9e04293296fc6bf3390241e4cac23c8145765b62d5
```

## Created files

No pre-existing file was modified by this task. New implementation files:

- [research package initializer](../src/ams/research/__init__.py)
- [offline orchestration](../src/ams/research/phase1.py)
- [IDs, seeds, serialization and hashing](../src/ams/research/phase1_common.py)
- [corpus, source records and grouping](../src/ams/research/phase1_data.py)
- [human annotation validation](../src/ams/research/phase1_annotations.py)
- [scenario assignment and event views](../src/ams/research/phase1_scenarios.py)
- [auxiliary stress recipes](../src/ams/research/phase1_stress.py)
- [private-key identifier blinding](../src/ams/research/phase1_blinding.py)
- [offline CLI](../scripts/prepare_mpbench_phase1.py)
- [fixed design configuration](../configs/research/mpbench_phase1.json)
- [offline tests](../tests/test_mpbench_phase1.py)

New documentation and validation files: this report,
[annotation guide](PHASE1_ANNOTATION_GUIDE.md), the four JSON evidence files linked
above, [artifact README](../research_data/README.md), and
[local generated-data ignore rules](../research_data/.gitignore).

Generated under [research_data/mpbench_phase1](../research_data/mpbench_phase1):
`composition_report.json`, `preparation_manifest.json`,
`public/candidate_inputs.jsonl`, `private/case_index.jsonl`,
`private/duplicate_groups.jsonl`, `private/blinded_packets.jsonl`,
`private/reviewer_a_template.jsonl`, `private/reviewer_b_template.jsonl`,
`private/adjudications_template.jsonl`, `private/utility_template.jsonl`,
`private/bag_validations_template.jsonl`, `private/group_review_template.json`,
and a private identifier-key file. Each `research_data/review_exports/reviewer_{a,b}/`
contains `packets.jsonl`, its blank `reviews_{a,b}.jsonl`, `utilities.jsonl` and
`instructions.json`. The blocked build has only `readiness_report.json`.

Existing repository ignore rules exclude `tests/` and `reports/`; the new
`research_data/.gitignore` excludes generated artifacts/reviews. Files exist locally
but are not all shown by ordinary Git status. A future release must explicitly
include the intended tests/reports and reviewed manifests while retaining private
blinding material until results are locked. No files were staged or committed.

## Boundaries, implementation choices and next steps

The exact controlled distribution and primary all-allow policies are unchanged.
Three routine details are explicit rather than silently assumed: tokenization uses
NFKC/case-folded Unicode word tokens; components larger than 32 are manually flagged;
and sampling conservatively forbids component reuse across all bags. The greedy
constructor can report failure even when a more complex allocation exists; it does
not weaken the split or quotas. The optional permission quarter uses a logical input
contribution root, with all its physical artifacts inheriting the restriction. Confirm
that interpretation before the separate permission study. It cannot create primary
transfer gains because that study is all-allow.

The public source catalog is a constructor artifact, not a streaming runtime input.
Future schedules and gold remain private. The runtime must receive only the trusted
cursor projection and must be isolated from evaluator files/tools. Schema checks
and Unix modes do **not** isolate arbitrary code under the same OS account. No
autonomous model runner or full claim/chunk/copy retrieval enforcement exists yet.
Public benchmark contents can also be externally matched; blinding is not a claim
of benchmark secrecy or absence of model contamination.

ASR, original retention, restraint, source-grounded QA and record/use classification
remain separate endpoints. There are no new metric values to report. Future episode
manifests supply exact denominators after reserved audits; the small-pool denominator
must not be replaced by the full-release 2,999 attack or 249 retention counts.

Proceed with the five missing-input steps above, using
[the annotation guide](PHASE1_ANNOTATION_GUIDE.md). Once complete packets/reviews
pass, run `build-pilot` into a fresh directory, review proposed bag selection hashes,
and rerun after final-bag validation. Freeze those artifacts and any amendments.
Only then begin the separately requested evidence-ledger/state implementation with
offline fixtures, followed by narrow retrieval integration and baseline parity.
Paid pilot execution still needs its own frozen arms, cost estimate and approval.
This preparation establishes no efficacy, natural-source generalization, novelty
over contextual/multi-scope reputation, or conference acceptance claim.
