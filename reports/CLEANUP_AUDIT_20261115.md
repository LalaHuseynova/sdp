# Checkpoint and temporary-file audit, and cleanup proposal (before step 2.1)

Status: **audit 15 Nov 2026; tiers 1 + 2 executed the same day with the owner's approval (§6). Tier 3 left unchanged.**

Repository on disk: **13 GB**. Largest parts:

| Path | Size |
|---|---|
| `research_data/` (116 dirs) | 5.3 GB |
| `reports/` | 3.3 GB |
| `third_party/` | 1.2 GB |
| `.venv/` | 1.0 GB |
| `.git/` | 1.0 GB |
| `.venv-minja/` | 909 MB |
| `data/` | 385 MB |
| `tmp/` | 266 MB |
| `results/` | 99 MB |

Outside the repo, `~/.cache/huggingface` is 924 MB.

## 1. How each item was checked
- **Code references:** every `research_data/` directory name was searched in `src/`, `scripts/`, `tests/` and `configs/`.
- **Documentation references:** the same names were searched in `README.md`, `plan.md`, `IMPLEMENTATION.md`, `brainstorm.md` and `reports/*.md`.
- **Data cross-references:** the same names were searched in other result directories' JSON and Markdown.
- **Paid ledgers:** found by their `dispatch.sqlite` and `budget.sqlite` files.
- **Duplicates:** files over 1 MB were compared by size and SHA-256. The RandEC zip was compared by CRC-32 with the extracted weights.
- **Git:** `git count-objects` and `git fsck --unreachable`.

## 2. Must keep (needed for v4 MPBench, paid caching, reproducibility, previous results)

| Path | Size | Why |
|---|---|---|
| `research_data/controlled_workload_session_v2_20261108/` | 82 MB | **paid ledger** (also the cost model's per-call source) |
| `research_data/controlled_workload_session_v3_20261112/` | 0.6 MB | **paid ledger** (current session) |
| `research_data/dynamic_execution_prep_v1_20261031/` | 119 MB | contains a **paid ledger** (`session/`); referenced by `transport.py`, `preflight.py` |
| `reports/safemem_full_mpbench/` | 2.6 GB | **paid response cache** `cache/responses.sqlite` plus the request budget; read by `native/pipeline.py`, `preflight.py`, `run_controlled_workload.py` and others |
| `.llm_cache/responses.sqlite` | 41 MB | LLM response cache; read by `src/ams/eval/context.py` |
| `research_data/provisional_api_receipts_v1_20261101/`, `published_paid_dev_v3_20261112/`, `adaptive_stage3_dev_v3_20261112/` | 83 MB | paid receipts and paid journals |
| `data/mpbench/`, `research_data/controlled_workload_v4_20261108/`, `workload_freeze_v4_20261108/` | 17 MB | **v4 MPBench**: source data, workload and freeze |
| `research_data/controlled_workload_stage1_test_v4_20261108/` | 499 MB | **v4 paid Stage-1 stores** (input of option B) |
| `research_data/controlled_workload_stage2_test_v4_20261108/`, `stage3_test_v4_20261108/` | 16 MB | locked v4 test results |
| `research_data/controlled_workload_v3_20261108/`, `stage1_dev_v3_20261108/`, `stage2/3_dev_v3_*`, `protocol_v2_*`, `archive_pre_protocol_v2_20261113/` and the sv2/adaptive/published exposure dirs | ≈ 0.55 GB | protocol v2 dev inputs and step 1.x results |
| `third_party/AMemGuard/.../distilbert_suffix.pt`, `~/.cache/huggingface` | 255 MB + 924 MB | RandEC weights and DistilBERT, offline |
| `mpbench_phase1`, `mpbench_provisional_v1`, `mpbench_recovery_v1`, `dynamic_native_stores_v1`, `provisional_*_freeze_v1`, `results/full_mpbench_reproduction/` | ≈ 1.3 GB | earlier results, referenced by code, tests (`test_mpbench_phase1`, `test_dynamic_planning`) and docs |
| `.git/` | 1.0 GB | committed history (unreachable objects are only 0.6 MB: nothing to clean) |

## 3. Proposed cleanup

### Tier 1: remove (verified duplicate or regenerable; no research data) — ≈ 1.0 GB

| # | Exact path | Size | Evidence | Risk and mitigation |
|---|---|---|---|---|
| 1a | `reports/downloads/randec-models.zip` | 707 MB | CRC-32 of all 3 members equals the extracted `third_party/AMemGuard/certified-llm-safety/models/*.pt` (35a49fe1, eb099741, a30d2299). No code reference. `scripts/fetch_third_party.sh` re-downloads it if needed. | If the upstream link disappears and `third_party/` is lost, the weights would be gone. **Mitigation:** first record the SHA-256 of the 3 `.pt` files in this report, or move the zip to external storage instead of deleting it. |
| 1b | `tmp/pdfs/result_table_tools/` | 265 MB | A Python virtualenv (pymupdf and others), used only as the interpreter for `scripts/render_research_result_tables.py` | Re-rendering the result-table PDFs needs the env rebuilt. **Mitigation:** save `pip freeze` to `tmp/pdfs/result_table_tools.requirements.txt` first. The rendered outputs in `tmp/pdfs/result_tables_*` (0.6 MB) are kept. |
| 1c | `__pycache__/` (outside `.venv*`), `.pytest_cache/`, `.ruff_cache/` | 29 MB | Caches, regenerated automatically | None |

### Tier 2: archive (compress, keep forever with a SHA-256 manifest) — ≈ 2.1 GB

| # | Exact path | Size | After compression | References | Risk and mitigation |
|---|---|---|---|---|---|
| 2a | `research_data/provisional_extension_results_v1_20261101/queries.sqlite` | 2.0 GB | ≈ 0.2 GB (gzip test: 200 MB → 19 MB) | 3 old v1 scripts (`inspect_research_state.py`, `report_development_comparison.py`, `diagnose_provisional_attacks.py`) and 1 data file; no test; not used by protocol v2 | Those v1 scripts fail until the file is restored (one command). |
| 2b | `research_data/provisional_comparison_results_v1_20261101/queries.sqlite` | 296 MB | ≈ 30 MB (100 MB → 9.7 MB) | The same 3 old scripts and 1 data file | Same |

**Procedure (per file):**
1. Record the SHA-256 of the original.
2. Write `queries.sqlite.tar.zst` next to it, in the same directory.
3. Extract to a temporary location and verify that the SHA-256 is identical.
4. Only then remove the uncompressed file.
5. Add `ARCHIVED.md` in the directory (original hash, size, restore command).

Directory paths, `comparison.json` and `comparison.md` stay where they are, so all document and data references keep resolving.

### Tier 3: optional, the owner's call (environments and unused models, not research data)

| # | Exact path | Size | Notes |
|---|---|---|---|
| 3a | `.venv-minja/` | 909 MB | No script or doc names it; the environment for the earlier MINJA attack demo (`third_party/MINJA`). Rebuilding later could pick up drifted package versions. **Recommendation:** keep unless the space is needed; if removed, save `pip freeze` first. |
| 3b | `third_party/AMemGuard/.../distilbert_insertion.pt`, `distilbert_infusion.pt` | 510 MB | Not referenced (protocol v2 uses `distilbert_suffix.pt` only). **Recommendation: keep.** They belong to the upstream release, and if 1a is done they are the only local copy. |

## 4. Looked at and NOT recommended
- **Pilot-finish intermediates** (28 dirs with no code or doc reference, 128 MB). They form a provenance chain: `pilot_finish_final_prefix` (cited by its report) → `normalized_current_view` → `corrected_prefix` → `development_prefix`, and so on. Archiving them breaks path resolution for little gain.
- **Duplicate files (454 MB in 19 groups).** These are by design: identical review packets given to reviewers 1–3, case indices shared across MPBench stages, and verification copies that are equal by construction. Removing them would weaken the review and provenance records.
- **`git gc` / pruning.** It would only repack committed history; the unreachable objects are 0.6 MB, and the 4 unreachable commits are dropped stashes from 14 Nov.
- **`data/longmemeval`, `data/mimic-iii*`, `third_party/MINJA`.** All are referenced by code or fetch scripts.

## 5. Expected savings

| Option | Savings | Repo after |
|---|---|---|
| Tier 1 | ≈ 1.0 GB | ≈ 12 GB |
| Tiers 1 + 2 (recommended) | ≈ 3.1 GB | ≈ 9.9 GB |
| Plus 3a | ≈ 4.0 GB | ≈ 9.0 GB |

## 6. Executed (15 Nov 2026, owner-approved tiers 1 + 2)

Records: `research_data/cleanup_20261115/`:
- `before.txt` and `after.txt` (du in KB);
- `randec_weights_sha256.txt`;
- `pycache_dirs_removed.txt`;
- `archive_sqlite.sh` and `tier2_archives.txt`;
- `result_table_tools.requirements.txt`.

| # | Action | Checks before acting | Freed (KB) |
|---|---|---|---|
| 1a | deleted `reports/downloads/randec-models.zip` | Not open by any process. `unzip -t` OK. CRC-32 of each member equals the kept `.pt` file. SHA-256 of the 3 kept weights and of the zip recorded. | 723,632 |
| 1b | removed `tmp/pdfs/result_table_tools/` | Package list (Python 3.11.15, 15 packages) and the rebuild command saved to `tmp/pdfs/result_table_tools.requirements.txt` | 271,540 |
| 1c | removed 30 `__pycache__/` dirs (outside `.venv*`; `.pyc` files only), `.pytest_cache/`, `.ruff_cache/` | Listed first; no other file inside | 29,464 |
| 2b | `provisional_comparison_results_v1_20261101/queries.sqlite` → `queries.sqlite.tar.gz` | Extracted OK; restored SHA-256 = original (`1801ce78…d785`); `integrity_check` ok | 273,384 |
| 2a | `provisional_extension_results_v1_20261101/queries.sqlite` → `queries.sqlite.tar.gz` | Extracted OK; restored SHA-256 = original (`a8776405…c984`); `integrity_check` ok | 1,917,588 |

**Measured result:**
- The repository went from **14,137,876 KB to 10,945,000 KB**, freeing **3,192,876 KB ≈ 3.05 GiB (3.27 GB)**.
- The disk's free space went from 7.27 GB to 10.22 GB.
- The per-item figures sum slightly higher (3,215,608 KB); the difference is du accounting.

**Restore instructions:** `ARCHIVED.md` in each tier-2 directory.

**Protected items unchanged** (newest modification time inside each predates the cleanup): the 3 paid ledgers, `reports/safemem_full_mpbench/cache`, `.llm_cache`, `data/mpbench`, v4 workload, freeze and Stage-1 / Stage-3 test data, the provisional freezes and the RandEC weights.
