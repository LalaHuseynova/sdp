#!/bin/bash
# LoCoMo-v1.2 (technical restart): paid -> judge-check -> analyse.
# Each stage re-verifies the freeze and the owner's approval. A stage continues only on exit 0:
#   paid: 3 = stopped (S2) or incomplete; judge-check: 5 = failed (canary or > 2%);
#   analyse: 6 = refused (stopped/incomplete run or no judge check).
# v1.1's script looked for the stop record in the wrong file and went on to analyse; this one
# relies on exit codes only.
# usage (Git Bash): MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash research_data/locomo_v1_2_pipeline.sh
set -u
cd /mnt/c/Users/HP/Documents/sdp
RUN=research_data/locomo_v1_run
R="bash research_data/locomo_v1_run.sh -m locomo_v1"

$R paid --run "$RUN" --workers 16
rc=$?
if [ "$rc" -ne 0 ]; then echo "STOPPED paid rc=$rc (no judge check, no analysis)"; exit "$rc"; fi

$R judge-check --run "$RUN"
rc=$?
if [ "$rc" -ne 0 ]; then echo "FAILED judge-check rc=$rc (no analysis)"; exit "$rc"; fi

$R analyse --run "$RUN"
rc=$?
if [ "$rc" -ne 0 ]; then echo "FAILED analyse rc=$rc"; exit "$rc"; fi
echo PIPELINE_DONE
