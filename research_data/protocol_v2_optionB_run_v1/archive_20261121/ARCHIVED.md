# Halted P-B2 attempts, archived 21 Nov 2026 (owner: "old or rerun folders ... less necessary compact")

`halted_attempts_20261121.tar.gz` (296,952,806 bytes) holds 311 files, verified member-by-member against
`halted_attempts_20261121.sha256.json` before the originals were removed (`scripts/archive_dir.py`):

- `sessions/`, `sessions_rerun1/`, `sessions_rerun2/`: paid ledgers of the halted P-B2 attempts (16-17 Nov; protocol §15 "kept as records")
- `gpt_rerun2/`: rerun-2 journal (used for the run-to-run agreement check, 98.89 %)
- `gpt.prompt_mirror/`, `gpt_rerun1.prompt_mirror/`, `gpt_rerun2.prompt_mirror/`: their verified prompt mirrors
- `conflict_replies.json`, `conflict_replies_rerun1.json`, `conflict_replies_rerun2.json`: their P-B1 replies
- `aborted_precompute_P3_restart/`: an aborted free precompute step
- `archive_20261119/v2_stage3_before_rev7_review/`: stage3 session copy taken before the revision-7 review

The halted original and rerun-1 journals and the full precompute are in `../archive_20261117/` (unchanged).

Restore (from the repository root): `tar xzf research_data/protocol_v2_optionB_run_v1/archive_20261121/halted_attempts_20261121.tar.gz`
then compare with the manifest. Nothing here is read by P-B3 or the analysis.
