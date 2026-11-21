#!/bin/sh
# One free per-group shard of the option-B runbook. Usage: shard.sh precompute|contexts G-Txx
set -u
cd /Users/ulkerhuseynova/Desktop/SAFE-Mem
export VIRTUAL_ENV=
RUN=research_data/protocol_v2_optionB_run_v1
B=research_data/controlled_workload_v4_20261108
S=research_data/controlled_workload_stage1_test_v4_20261108
step=$1; g=$2
if [ "$step" = precompute ]; then
  uv run python scripts/run_protocol_v2.py precompute --bundle $B --stage1 $S --groups $g \
    --out $RUN/precompute/$g --methods static R C M S SL S2-BS > $RUN/logs/precompute_$g.log 2>&1
else
  uv run python scripts/run_protocol_v2.py contexts --bundle $B --stage1 $S --groups $g \
    --replies $RUN/conflict_replies.json --out $RUN/contexts/$g > $RUN/logs/contexts_$g.log 2>&1
fi
rc=$?
if [ $rc -eq 0 ]; then echo "done $step $g"; else echo "FAILED $step $g rc=$rc"; fi
