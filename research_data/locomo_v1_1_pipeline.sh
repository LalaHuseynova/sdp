#!/bin/bash
# LoCoMo-v1.1: paid -> judge-check -> analyse (each stage re-verifies the freeze and approval)
cd /mnt/c/Users/HP/Documents/sdp
R="bash research_data/locomo_v1_run.sh -m locomo_v1"
$R paid --run research_data/locomo_v1_run --workers 16 || { echo "PAID_FAILED $?"; exit 1; }
grep -q '"stop"' research_data/locomo_v1_run/progress.jsonl 2>/dev/null && { echo "STOPPED_S2"; exit 2; }
$R judge-check --run research_data/locomo_v1_run || { echo "JUDGECHECK_FAILED $?"; exit 3; }
$R analyse --run research_data/locomo_v1_run > research_data/locomo_v1_run/analyse.log 2>&1 || { echo "ANALYSE_FAILED $?"; exit 4; }
echo PIPELINE_DONE
