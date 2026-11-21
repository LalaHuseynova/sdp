# Cleanup audit, 21 Nov 2026 (after P-B2, before P-B3)

**Owner instruction (21 Nov):** "if old or rerun folders which don't affect our idea and old files and folders which won't be used for the future please most unnecessary ones delete, less necessary compact".
Method as in `reports/CLEANUP_AUDIT_20261115.md`: code/test references searched in `src/`, `scripts/`, `tests/`, `configs/`; items in the
15 Nov "must keep" list, in the rev7 freeze, or read by code or tests were not touched. Records: `research_data/cleanup_20261121/`.

## Deleted (no research data, regenerable, or recoverable from git)

| Item | Size | Why safe | Record |
|---|---|---|---|
| `.venv-minja/` | 909 MB | Python environment for the old MINJA demo; no code or test reference (15 Nov tier 3a) | package list + Python version: `venv_minja_requirements.txt` (rebuild: `uv venv .venv-minja --python 3.11 && uv pip install --python .venv-minja/bin/python -r ...`) |
| 4 practice folders: `controlled_workload_dryrun_dev_v1_20261108`, `controlled_workload_v2_dryrun_dev_20261108`, `controlled_workload_v4_dryrun_dev_20261108`, `controlled_workload_stage3_dev_v3_mock_20261108` | ≈ 20 MB | Dry runs and a mock (no paid call, no result used anywhere); no code or test reference; 18 of their 22 files are in git history | SHA-256 of every file: `deleted_files_sha256.txt` |
| `README_BEFORE_RESEARCH_20261101.md` | 10 KB | Old copy of the README before the research (upstream text + OpenRouter setup); in git history | `deleted_files_sha256.txt` |
| 28 `__pycache__/` dirs (outside `.venv*`), `.pytest_cache/`, `.ruff_cache/` | < 1 MB | Caches, regenerated automatically | `pycache_dirs_removed.txt` |

## Compacted (kept forever, verified)

| Item | Before | After | Record |
|---|---|---|---|
| Halted P-B2 attempts: `sessions/`, `sessions_rerun1/`, `sessions_rerun2/` (paid ledgers), `gpt_rerun2/`, 3 prompt mirrors, 3 old `conflict_replies*.json`, `aborted_precompute_P3_restart/`, `archive_20261119/` | 1.2 GB, 311 files | 297 MB: `research_data/protocol_v2_optionB_run_v1/archive_20261121/halted_attempts_20261121.tar.gz` | every member re-read and matched to `halted_attempts_20261121.sha256.json` before the originals were removed (`scripts/archive_dir.py`); restore steps in `ARCHIVED.md` |

## Not touched (and why)

- Current run: `gpt_rerun3/`, `sessions_rerun3/`, `gpt_rerun3.prompt_mirror/`, `contexts/`, `precompute/`, `conflict_replies_rerun3.json`, `analysis_gpt_early/`, `scripts/`, `logs/`, `archive_20261117/` (already compressed).
- Frozen inputs (rev7 freeze): v3/v4 workloads and Stage-1 stores, `data/mpbench`, RandEC weights, Hugging Face snapshots.
- The first MPBench phase folders (29 Oct-1 Nov): several are read by code and tests (`mpbench_phase1`, `mpbench_provisional_v1`, `mpbench_recovery_v1`, `dynamic_native_stores_v1`, provisional freezes), and the pilot-finish chain is provenance (15 Nov §4). Small gain, real risk.
- `reports/safemem_full_mpbench/` (2.6 GB paid response cache, read by code), `results/` (read by code), `third_party/`, paid ledgers listed on 15 Nov.

## Checks after the cleanup

| Check | Result |
|---|---|
| rev7 freeze verify | verified, 320 files |
| locked protocol v1 verify | verified, 224 files |
| pre-v2 snapshot verify | differs, **changed 0, missing 25** = the 3 files of the 15 Nov cleanup + the 22 practice-folder files deleted here (all listed with SHA-256) |
| P-B2 ledgers (`stop_safe_pb2.sh --check`) | clean |
| Full test suite | **833 passed** |

**New expected RUNBOOK §1 result before P-B3:** `verified`; `verified` (224); `differs` with `changed: 0, missing: 25`.

## Space

Repository 20,084,456 KB → 18,114,128 KB: **1,970,328 KB ≈ 1.9 GiB freed**. Disk free 7.4 GiB → 9.2 GiB.
