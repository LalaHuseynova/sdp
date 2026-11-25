# Repository review and cleanup — 7 November 2026

## Outcome

The repository contains a completed Original SAFE-Mem reproduction, an implemented minimum selective-propagation prototype, and a completed preliminary development comparison. The reported counts agree with saved outputs. The selective method has not demonstrated an advantage over contextual or multi-scope reputation. Human validation, the final safety-balanced pilot and a full-dataset run of our method remain pending.

This task changed documentation and removed confirmed disposable files. It did not implement a research feature, change a policy, regenerate a dataset, revise annotations, train a model or make a paid API call.

## What was inspected

- Root and module READMEs, the research proposal, implementation roadmap, primary protocol, provisional design, reproduction report and preliminary result report.
- The code structure and key implementation paths: provisional case selection/assignment, risk policies, ledger scope support, retrieval admission/ranking, recovery/native integrity checks, sequential execution and guarded execution interfaces.
- Saved preparation, recovery, provisional-group and native-store manifests; both comparison freezes; saved human-review readiness; official dataset hashes; original memory/core/prompt files; recorded source dependencies and the shared local budget state.
- Original reproduction answers and the 3,888 preliminary comparison outcomes, using the existing offline inspection script.
- Exact-byte duplicates across the project tree, with environments, `.git`, third-party dependencies and the top-level model-response cache excluded. Secrets were not read. Interpreter/test/lint caches were inventoried separately. The temporary PDF-tool environment under `tmp/` was included in the inventory but preserved as a dependency.

This was a repository/documentation consistency review, selected implementation inspection and a complete run of the existing offline suite. It is not a new line-by-line proof of every module, an audit of third-party packages, an independent safety annotation exercise or a new literature review.

## Validation

| Check | Result |
|---|---|
| Existing offline suite | Passed: 612 JUnit testcase records; zero failures, errors or skips. The suite-level XML counter is 670, including additional subtest accounting; it is not 670 distinct collected test functions. |
| Original source inventory | 6,240 unique ingestions checked. |
| Original reproduction recount | 5,996 readable outcomes; ASR 176/2,999, retention 213/249, restraint 1,273/2,607, combined benign 1,486/2,856. |
| Preliminary comparison recount | 3,888 saved outcomes; 18 method/condition combinations, four metrics each. |
| Provisional preparation | 20 groups and 120 overlays verified; zero human-verified labels. |
| Native stores | 442 dependencies and 62 payloads checked. Scientific pilot readiness remains false. |
| Original memory/core/prompts | Existing integrity check passed. |
| Previous result delivery | Existing 99-file integrity check passed. |
| Local research budget | USD 2.09412345 used, USD 27.90587655 remaining, zero holds; no new paid requests. This is not a new provider-account reconciliation. |
| Code preservation during cleanup | All 423 snapshotted Python/shell/config/prompt/test files unchanged. |

Evidence: [saved-state inspection](REPOSITORY_REVIEW_20261107_STATE.json), [test XML](REPOSITORY_REVIEW_20261107_TESTS.xml), [cleanup inventory and exact deletions](REPOSITORY_CLEANUP_20261107_MANIFEST.json).

The known legacy Phase 1 validator refusal persists: its fingerprint scope includes unrelated added research modules. The recorded original producer files and payloads pass direct checks, but affected legacy regeneration/import commands are not ready for reuse. No manifest was rewritten and no gate was bypassed to hide this issue.

## Documentation changes

- Updated the [root README](../README.md): current inspection date, reading order, plain-language aim, memory creation, audit/query flow, three conditions, numbered 15-step status table and the next research question.
- Added the [research code README](../src/ams/research/README.md): stage-by-stage file map, source relationships, evidence updates, policy arithmetic, retrieval integration, actual execution scope and data locations.
- Added the [script README](../scripts/README.md): entry points grouped by purpose, offline versus potentially paid work, and why similarly named commands are not redundant.
- Added the [report README](README.md): current results, historical proposals, human-review guides and retained failed checks.
- Added current-status notes to nine module READMEs: dynamic, retrieval, sequential, native, planning, execution, llm_review, llm_followup and ai_pilot. Their interface descriptions and historical scope remain available. In particular, the old inactive USD 125 plan is explicitly distinguished from the USD 30 allowance.

The old primary protocol and dated reports were not rewritten. The root README is the current status entry point. No newer result was inferred from a prepared file or a passing engineering test.

## Duplicate-file decisions

The inventory scanned **8,128 non-cache files** and found **284 groups of identical nonempty files**. Identical bytes alone do not make a file disposable.

There are no exact duplicate nonempty implementations *within* `src/`, `scripts/`, `tests/` and `configs/`. The table-rendering script has an identical copy in the delivered table bundle; it is covered by that bundle's manifest and was kept. This exact-byte scan does not claim to detect all repeated logic or near-duplicate code.

Deleted **241 files totaling 6,228,909 bytes**:

- Five redundant scratch copies under `tmp/pdfs/result_tables_draft_v2/`: two PNG tables and their source-data JSON, identical to retained delivered files; two preview PNGs, identical to retained final-QA previews.
- 236 disposable files from project Python bytecode caches, pytest/ruff caches and Finder metadata. Empty cache directories were removed afterward. These files may be recreated by later tools.

Each deletion has a path, content hash, size and reason in the cleanup manifest. Each deleted substantive scratch copy also names the retained identical file. Unique scratch drafts were not removed.

Preserved intentionally:

| Files/folders | Why they stay |
|---|---|
| Original and previous READMEs | They contain different historical/setup information and attribution. |
| `research_data/` versioned bundles | Frozen inputs, joins and review states are referenced by manifests and results. |
| Independent reviewer packets/forms | Equal starting content is intentional; reviewers need separate workspaces and decisions. |
| Earlier failed/partial AI-review versions | They document failed controls, coverage changes and spending. |
| Reproduction run attempts and report snapshots | They preserve interrupted execution, dataset identity and accounting history. |
| Separate original and revised presentation directories | They are different decks; matching internal XML pieces do not make the directories redundant. |
| Delivered tables and bundled generator | The delivery manifest protects a self-contained artifact. |
| `.venv`, `.venv-minja`, temporary PDF-tool environment | They serve different dependency needs; deleting them could require reinstallation. |
| Model-response caches, SQLite databases and billing journals | Required for offline recovery, replay and cumulative spending controls. |

No source file or research-data directory was moved or deleted. This avoids breaking imports, CLI paths, frozen hashes and report links. Clarity comes from the new code/script indexes, not from collapsing scientifically distinct versions.

## Remaining limitations and next step

1. Human safety/provenance and utility-question validation are still missing.
2. The primary verified 16-safe/16-unsafe pilot has not been generated or executed.
3. The preliminary workload admitted few attributed external candidates. Examine the 23 changed contexts and remaining attack successes before redesigning the evaluation.
4. Prospectively define tasks that legitimately need external memories while retaining principal-owned controls. Preserve authority and apply any new setting equally to every method. Do not choose tasks based on whether S wins.
5. Stronger baseline variants, answer-level robustness, full-dataset S evaluation and external validation are unfinished.
6. Release packaging is pending. Much research code is untracked, and `.gitignore` excludes tests/reports. Nothing was committed or published in this cleanup; private evaluator material still needs separate release handling.

These are remaining research or packaging tasks, not hidden implementations performed during this review.
