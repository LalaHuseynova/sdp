# Native memory construction and provenance bindings

31 October 2026. **The next engineering step is complete for the 20 existing
provisional groups.** New research-owned native stores were constructed through
Original SAFE-Mem using existing cached responses only. No API call, model
download, dependency installation, training, answer/retrieval experiment, human
annotation or final validated pilot generation was performed.

**Additional API cost: USD 0.** The existing shared API allowance remains
**USD 30 total, USD 0 charged, USD 0 held**. No new allowance was created.

## What was produced

The [native preparation bundle](../research_data/dynamic_native_stores_v1_20261031/preparation_report.json)
contains one base snapshot per provisional group, a construction crosswalk and
R/C/M/S loading descriptors. Existing provisional groups were reused, not
resampled or relabeled. These groups remain case-intent-controlled, not verified
16-safe/16-unsafe pilot groups.

| Item | Result |
| --- | ---: |
| Native stores prepared / unavailable | **20 / 0** |
| Existing contributions represented | **640** |
| Matched claims | **2,580** |
| Matched evidence chunks | **13,284** |
| Actual native source bindings | **24,177** |
| Actual native claim/chunk bindings | **15,864** |
| Unknown external-origin roots | **640** |
| Separate principal roots with stored records | **50** |
| Cached original-question catalogs | **640 questions** |
| Revealed safety verdicts / spent audit tickets | **0 / 0** |
| Independently verified safety labels / validated utility questions | **0 / 0** |

The scope is the 640 selected provisional inputs, not all 6,240 original source
cases. Every native store covers its complete existing 32-case bag. Missing or
mismatched records would have made that store unavailable rather than producing
a falsely complete snapshot; no such store failure occurred.

## New implementation

| Component | Function |
| --- | --- |
| [Cache-only client](../src/ams/research/native/cache.py) | Exact request-key lookup in immutable existing caches; strict chat/model/vector checks and no fallback |
| [Construction observer and bindings](../src/ams/research/native/construction.py) | Original write calls with source-allocation observation, exact source spans and conservative provenance |
| [Preparation, verification and arm loading](../src/ams/research/native/pipeline.py) | Complete native graph/index/client snapshots, frozen write/query tables, manifests and independent arm instances |
| [CLI](../scripts/prepare_dynamic_native.py) | Socket-blocked prepare/check commands; no paid-execution switch |
| [Tests](../tests/test_dynamic_native.py) | 16 offline checks with invented sources and temporary caches |
| [Usage and limitations](../src/ams/research/native/README.md) | Artifact formats, attribution rules, loading examples and remaining scientific requirements |

Only new files were added. Original SAFE-Mem, MPBench bytes, previous research
code, caches, preparation outputs and human-review forms were preserved.

## How fidelity was checked

Each bag uses its existing COMMON provisional-ingestion order. Original
`TypedStandingMemory.write` performs retention, extraction, entity construction,
authority assignment, sentence segmentation, embedding-dependent chunking and
index insertion. Responses and vectors come from exact existing cache keys;
there is no provider factory, credential loading, model fallback or cache write.

The construction observer tracks new principal/artifact roots and the sentence
nodes created from each actual parent. Display labels and lexical similarity
are not join keys for trusted provenance. The observer is removed after
construction; the runtime memory has exactly the original
`TypedStandingMemory` type.

For each claim, checks match saved/recovered count, order, raw text/hash, claim
type, standing, usable kind, subject, initial contested flag and structural parent
artifact. For each chunk, they match count, order, text/hash, parent artifact and
exact supporting source spans. Native graph/index/binding consistency and
original-query classifier/embedding coverage are validated before publishing a
complete snapshot.

Native IDs are newly allocated. They are explicitly crosswalked to stable
recovered logical record IDs after these checks. Historical IDs are never
assumed to be valid IDs in a new store. Repeated artifact display labels and
identical text remain separate sources when their construction identities differ.

Original `max_claims=6` applies per extraction call. Separate principal/external
passes produce more than six total claims in three selected contributions. This
original behavior and all recovered claims were retained; no new case-wide
truncation was introduced.

## Attribution and scientific boundaries

Principal-authored records remain under the original `user` task principal and
separate roots. External origins remain **unknown**, with no authenticated
contributor ID assigned by this builder. Original `_overlap` claim assignment is
retained only as a structural parent; it cannot create reputation evidence.
Ambiguous external claims inherit all plausible contribution-artifact policies.

The initial evidence snapshots contain only provenance registrations. They
contain no safe/unsafe vote, expected target, attack-case label, hidden risk
profile, method outcome or future audit result. Literal claim-support matches
remain unreviewed candidates. Source/body attribution does not establish
safe-for-use ground truth.

These stores do not silently promote an innocent uploader to culpable origin.
Independently checked attribution and the declared synthetic contributor/batch
overlay must be applied in a new initial-state version before the scientific
propagation experiment. Until then, unknown roots cannot drive contributor
penalties. Genuine reviews and existing annotation packet hashes were not
invented or overwritten.

These are **new stores**, not a replay of the complete historical 6,240-case
graph or its query/conflict history. Visible historical claim metadata and
recovered text/spans match. Complete historical object/relation fields were not
saved and are not independently verified; the new stores obtain them from the
exact cached extractor replies. The future static baseline and all methods must
use this same workload and initial state.

## Restart, arm independence and prompt inspection

One compressed immutable snapshot per group avoids four redundant disk copies.
Each `load_store(..., arm)` creates a fresh graph, indexes, clients and classifier
cache. All arms start from the same content, construction history and governance
state; their comparison policy is the explicit difference. Conflict mutations
cannot be shared across arm instances.

All 20 saved stores were restored from disk and revalidated: **24,177 source
bindings and 15,864 record bindings**. The first store was also loaded into two
arms and compared for equal non-policy state with distinct mutable objects.
No retrieval request, answer or target judgment was executed.

The crosswalks include longest-field prompt inspection, without candidate
retrieval or model calls. Answer proxies span **5,591–6,671** and conflict proxies
**1,644–1,714**, using the existing UTF-8 bytes/scaffolding convention. They are
not native GPT token measurements or guaranteed tokenization bounds. They apply
to the initial stores and supplied original questions; finalized utility
questions or later state changes require refreshed inspection and costing.
The spending guard's full-context reservations remain independent of these
proxies. No paid utility-question classifier preparation was performed.

## Validation and preservation

**341 tests and 31 subtests passed**, including all 16 new native-construction
checks and the existing preparation, ledger, policy, retrieval, restart, planning
and spending-guard tests. Ruff lint and formatting checks passed.

New tests check original-write parity, type/standing/source/chunk mismatches,
offline cache misses, malformed vectors, duplicated text/display labels, separate
principal/unknown roots, zero invented audit observations, missing query
catalogs, unchanged cache bytes, independent arm objects, compressed artifact
loading, no overwrite, hash tampering and path/arm rejection. Test sources and
vectors are explicitly artificial, not human annotations or MPBench outcomes.

The native bundle verifies **62 payload files and 442 dependencies**. Runtime
snapshots contain no executable callback or serialized provider/SDK. The bundle
occupies approximately 207 MiB; previous outputs were not replaced.

[Preservation before](NATIVE_STORES_20261031_INTEGRITY_BEFORE.json),
[preservation after](NATIVE_STORES_20261031_INTEGRITY_AFTER.json),
[on-disk restart checks](NATIVE_STORES_20261031_RESTART_CHECK.json), and
[validation record](NATIVE_STORES_20261031_VALIDATION.json) contain the checks.

## Remaining requirements

Native-store construction and structural bindings for these provisional bags are
now available. Human review is still pending: the current forms contain zero
independently verified safety labels and zero validated utility questions.

Before paid scientific execution:

1. Validate safety/provenance and useful benign questions, and resolve ambiguous
   origins using evidence rather than lexical overlap.
2. Freeze the final Z-balanced groups, exact audit/probe cohorts and permissions.
   Reuse this builder for the finalized selection; current provisional groups
   must not be relabeled as validated.
3. Apply the checked provenance/contributor overlay in a new initial-state version
   and provision only the selected utility-question catalogs/local embeddings.
4. Refresh exact prompt/call costs and scientific execution preflight, keeping
   every arm/control under the same existing USD 30 allowance.

No additional API cost was needed to finish this engineering step. Any future
paid work still requires an advance estimate, as the user requested.
