# Steps 3–5: memory recovery and annotation preparation

29 October 2026. **Memory text and construction provenance have been recovered for
all 6,240 source contributions. Independent human annotations remain pending. The
32-case pilot is not ready, and no final pilot groups were generated.**

No model inference, API request, model/dependency download, training, defense
evaluation, trust update or selective propagation was performed. The work reused
Phase 1 source records, identifiers, groups and packets rather than redoing the
corpus inventory or constructing a new synthetic overlay.

## 1. Recovery results

| Recovery status | Claims | Evidence chunks | Contribution bundles |
|---|---:|---:|---:|
| Directly recovered from saved artifacts | 22,089 | 318 | 0 |
| Reconstructed and historically verified within the scope below | 0 | 123,772 | 6,240 |
| Reconstructed but historically unverified | 0 | 0 | 0 |
| Unavailable offline | 0 | 0 | 0 |
| Total | 22,089 | 124,090 | 6,240 |

There are **zero partial bundles** in the recovered text/construction-parent scope.
A bundle containing reconstructed members is categorized as reconstructed even
when its claims were directly saved. It is not promoted to directly recovered.
Complete recovery does not mean the source is safe or its natural author authenticated.

The original claim text, IDs and case ownership come from the saved write journal.
Its full original write metadata remains available in that unchanged, fingerprinted
input journal; no claim extraction was rerun. Chunk text was reconstructed using
the original segmentation and `cut` algorithm with the original cached MiniLM
sentence vectors. No model was loaded. Retention decisions controlling whether
principal sentences were indexed were read from existing cached responses, not
newly classified.

Verification used multiple persisted artifacts, not matching counts alone:

- 36,702 embedding-cache lookups and 6,240 cached retention-response lookups; zero misses.
- Cached ordered chunk-batch request keys commit to the exact reconstructed text
  lists, provider and model. Each response is bound by its saved payload hash.
- All **22,089 saved claim allocation IDs** match replay of source/sentence/chunk/claim
  allocation order. All **22,089 saved parent-source references** resolve to the
  reconstructed contribution's original source roots.
- All **318 unique evidence chunks observed in saved retrievals** match their
  reconstructed legacy IDs, plaintext and source labels. Repeated exposures count
  as observations of the same record, not new records or independent incidents.
- The reconstructed total of 124,090 chunks agrees with saved graph statistics.
  There are no unmatched observed chunk IDs, rendering disagreements or allocation
  anchor mismatches.
- The recovered chunk catalog passes the existing Phase 1 evidence importer for
  all 6,240 source cases and all 124,090 chunk records.

**Verification scope:** these checks support exact text, allocation and mechanical
construction parents. Some cache commitments originate in prefetch. This is not an
independently saved full graph dump, a complete replay of contested flags or standing
changes, a recreation of all answer contexts, or proof of answer equivalence. No
benchmark was rerun. The evidence does not authenticate email signatures, accounts
or semantic claim attribution.

The original memory package is not instantiated by the recovery runner. It loads
the existing pure `cut` function from its syntax tree and reuses the original pure
segmentation/cosine code. Cache-key encoding and retention-response interpretation
match the original code. The cache is opened with SQLite `mode=ro&immutable=1`;
nonempty WAL files are refused. Socket connections and DNS are blocked during
execution. There is no provider fallback, API client or model download path.

## 2. Provenance and annotation preparation

All 2,114 existing Email/File-Document packets were versioned and updated:

| Actual records in updated review population | Count |
|---|---:|
| Saved claims | 8,544 |
| Recovered evidence chunks | 44,172 |
| Total record/use review items | 52,716 |
| Packets | 2,114 |
| Packets with no memory records after recovery | 0 |

The 241 formerly claim-empty packets now contain recovered chunks. Their existence
does **not** make those bundles safe, and it does not guarantee their content is
eligible under the frozen original retrieval configuration.

Chunks carry exact artifact-local, potentially discontiguous supporting spans.
Principal turns remain separate from external source bodies. Source boundaries and
legacy graph parent mappings are mechanically checked. Claims retain unreviewed
literal support proposals where present; paraphrases are not given invented spans.
Semantic support and natural authorship remain unverified. No source username,
uploader account or blame attribution was inferred from document text.

Reviewer 1, Reviewer 2 and disagreement-adjudicator folders contain the same blinded
packets with blank forms. Source-case labels, `expected_memory`, original/legacy
identifiers, cached retention decisions, risk profiles and method outputs are absent
from the reviewer schema. Original task/source wording is preserved; it may naturally
contain suspicious instructions. Original public benchmark content can still be
recognized externally; the workflow does not claim benchmark secrecy.

The importer reuses Phase 1's independent-review, span, hash and adjudication checks.
It additionally prevents partial or historically unverified bundles from being
counted as complete eligible bundles. It preserves original votes and requires a
new output version. It does not rewrite packet hashes to migrate old votes.

**Actual human annotation coverage:**

| Independently verified outcome | Record/use labels | Bundle labels |
|---|---:|---:|
| Safe for this use | 0 | 0 |
| Unsafe for this use | 0 | 0 |
| Uncertain | 0 | 0 |

No genuine independent reviews were supplied. All 2,114 packets await the two
initial reviews; there are no real disagreements or adjudications yet. Unknown
annotations are pending, not automatically labeled uncertain or safe. Artificial
reviewer IDs used by tests exist only in test fixtures, not the real review outputs.

## 3. Candidate benign-use questions

The current question revision is
`research_data/mpbench_utility_v2_20261029/`. Earlier initial/header drafts and the
first utility revision are preserved; they are superseded for subsequent QA review.
This revision reused the completed recovery without rerunning chunk reconstruction.

| Current candidate coverage | Count |
|---|---:|
| Contributions with an automatically drafted question | 1,446 |
| Claim-supported candidates | 817 |
| External-chunk-only candidates, blocked under frozen settings | 629 |
| Contributions without an automatic candidate | 668 |
| Human-validated questions/references | 0 |
| Independently safe source contributions for these candidates | 0 |
| Eligible validated benign-utility questions | 0 |

The 1,446 drafts cover 1,061 email and 385 file/document contributions. Of the
817 claim-supported drafts, 434 are email and 383 file/document. Automatic rules
extract structured source fields or literal answer phrases from existing claims;
they do not write replacement memories or use attack labels/expected targets.
All answer values have exact source spans and supporting actual record IDs.
Every draft is marked **safety-unverified**, **unvalidated**, and ineligible for
the final benign set pending review.

Literal matches do not prove entailment. Some questions about descriptions or
metadata may be vague, grammatically weak, ambiguous or unhelpful. Humans must
reject or revise them, validate references and safe new descriptive use, and later
check unique/disambiguated support in the eventual selected group.

The frozen baseline has `external_evidence=false`. A question supported only by an
external chunk cannot be credited as usable retained external memory under that
setting. Such drafts are explicitly blocked from final utility eligibility. Two
positive human QA votes alone do not override that restriction. Claim-supported
questions still need independently safe external-source attribution and later
governance checks; their presence does not certify readiness.

Claim-supported automatic draft counts by original case category are:

| Context | Attack-input cases | Explicit benign | Suggestive benign |
|---|---:|---:|---:|
| Email | 196 | 4 | 234 |
| File/document | 239 | 5 | 139 |

These are **draft counts by original input labels**, not verified safety labels or
eligible-case counts. The protocol requires 20 explicit benign safe contributions
per context across 20 bags. Even if all existing explicit drafts were validated,
at least 16 additional email and 15 file/document explicit-source questions would
need manual authoring/validation. Some contributions may not contain usable external
information at all; that is a capacity question, not a reason to relabel principal
preferences, invent facts or enable a different retrieval setting.

## 4. Balance and pilot readiness

The original review population remains 1,061 email and 1,053 file/document cases:

| Context | Original attack inputs | Explicit benign | Suggestive benign |
|---|---:|---:|---:|
| Email | 549 | 39 | 473 |
| File/document | 551 | 36 | 466 |

Case labels and record/use labels remain separate. Existing duplicate/template
components and development/evaluation separation requirements were retained; no
case, label, threshold, context or quota was changed to fill a bag. No contributor
assignments, final pilot groups, propagation policies or trust updates were created.

The protocol still needs, per context and per 32-case bag, eight unsafe adversarial
bundles, two safe adversarial bundles, one safe explicit benign and five safe
suggestive benign bundles. This gives 16 unsafe/16 safe bundles and 20 attack/12
benign input labels overall. Across 20 bags the per-context requirements remain
160/40/20/100 for those respective strata.

**Independently eligible cases currently: zero in every required stratum.** Complete
record recovery has removed the missing-chunk blocker; it has not supplied any
safety labels. Whether 40 genuinely safe adversarial bundles per domain exist under
complete record/use review remains unknown. If a required stratum or group separation
is infeasible, document and amend the protocol before outcome evaluation. Do not
force labels, substitute easier attacks or silently reuse templates.

## 5. Validation and preservation

- **23 new offline tests passed.** These cover exact cache keys; read-only/cache-miss
  behavior; network denial; nonempty-WAL refusal; original similarity/cap chunking;
  Unicode/bullet/discontiguous spans; text commitments and saved ID anchors; direct
  saved retrievals; mismatches despite equal counts; partial bundles; unavailable
  retention/cache data; deduplicated observations; packet versioning; blinding;
  exact candidate spans; actual-claim support; missing reviews; independent reviewers;
  stale hashes; QA validation; blocked external chunks; and reproducibility.
- Targeted Ruff checks pass. The completed 35 Phase 1/identity tests were not
  unnecessarily rerun; existing Phase 1 code/output fingerprint validation passed.
- All 27 listed recovery output files validate against their manifest, with exact
  packet record hashes and source spans. Latest utility candidates are separately
  fingerprinted and versioned. Empty review ingestion reports zero genuine labels.
- Before/after protected-file checks cover 330 pre-existing files, including the
  original MPBench files, baseline code/config/prompts, Phase 1 outputs, historical
  run files and both response databases. See the JSON proof files below for results.

Machine-readable evidence:
[before fingerprints](RECOVERY_20261029_INTEGRITY_BEFORE.json),
[after integrity check](RECOVERY_20261029_INTEGRITY_AFTER.json),
[validation results](RECOVERY_20261029_VALIDATION.json),
[consolidated readiness](RECOVERY_20261029_SUMMARY.json).

Private record files use mode 0600 and private directories 0700. This separates
serialized views but does not sandbox arbitrary code under the same OS identity.
A future defense must not have evaluator files or filesystem tools exposing them.
This step implements no autonomous defense runtime.

## 6. New files and use

New implementation files, separate from original SAFE-Mem and Phase 1:

- [package initializer](../src/ams/research/recovery/__init__.py)
- [offline cache and network guard](../src/ams/research/recovery/offline.py)
- [record recovery and historical verification](../src/ams/research/recovery/records.py)
- [blinded annotation and utility drafting](../src/ams/research/recovery/annotation.py)
- [versioned preparation/import pipeline](../src/ams/research/recovery/pipeline.py)
- [offline CLI](../scripts/prepare_mpbench_recovery.py)
- [new offline tests](../tests/test_mpbench_recovery.py)

New documentation: this report and the
[human review guide](RECOVERY_20261029_REVIEW_GUIDE.md). New proof files are linked
above. Existing source files, original data, protocols and previous review packets
were not modified. Existing working-tree changes were preserved.

Generated recovery root: `research_data/mpbench_recovery_v1_20261029/`.
It contains `recovery_manifest.json`, `recovery_readiness_report.json`,
`public/source_links.jsonl`, and private `claims.jsonl`, `evidence_chunks.jsonl`,
`bundle_index.jsonl`, `recovered_evidence_catalog.jsonl`, `review_packets.jsonl`,
`packet_versions.json`, `utility_candidates.jsonl`, `utility_candidate_coverage.json`,
`annotation_coverage.json`, and `evaluator_case_index.jsonl`.
Three reviewer folders contain identical blinded packets, blank safety/provenance
forms, initial utility drafts/forms, and instructions. Use the **latest v2** utility
folders instead for candidate QA review.

`research_data/mpbench_utility_v1_20261029/` preserves the intermediate claim-support
revision. `research_data/mpbench_utility_v2_20261029/` contains the current private
candidate/coverage files, separate reviewer QA folders and a utility manifest.
`research_data/mpbench_review_coverage_v{1,2}_20261029/` contains versioned review-import
coverage and manifest files; v2 references the current utility candidates. Neither
contains fabricated completed reviews. Generated roots have local data-ignore rules;
the scientific payload fingerprints are recorded separately from those admin files.

Commands:

```sh
PYTHONPATH=src .venv/bin/python scripts/prepare_mpbench_recovery.py validate \
  --prepared research_data/mpbench_recovery_v1_20261029
PYTHONPATH=src .venv/bin/python -m pytest -o addopts='' tests/test_mpbench_recovery.py -q
.venv/bin/ruff check src/ams/research/recovery scripts/prepare_mpbench_recovery.py \
  tests/test_mpbench_recovery.py
```

The CLI refuses existing output directories. It provides `recover`, `validate`,
`prepare-utility`, and `import-reviews`; none invokes a model or constructs pilot groups.

## 7. Exact next steps

1. Assign two genuine independent reviewers to the updated full memory packets;
   use a third person only for actual disagreements. Review source attribution and
   the stated use separately, preserving uncertain and pending items.
2. Independently validate or revise the current claim-supported utility drafts.
   Author missing substantive questions from actual safe external contributions,
   especially the scarce explicit-benign strata. Leave blocked chunk-only drafts
   out of the frozen-setting utility set. Never relabel principal facts as external.
3. Import real votes and QA validations into a fresh coverage version, using the
   commands and schemas in the review guide. Confirm safe/unsafe/uncertain counts
   and provenance uncertainty by exact record/use and contribution units.
4. Check the required 160/40/20/100 per-context strata for 20 bags and independent
   template groups. If not feasible, record the limitation before any outcome tuning.
5. Only after those prerequisites, separately request proposed bag construction and
   final per-group support-uniqueness review. Freeze accepted manifests before any
   future defense implementation/evaluation. No pilot generation is authorized or
   performed by this preparation command.

This work provides recovered records and annotation-ready materials. It does not
establish defense efficacy, a novelty claim or ICML acceptance prospects.
