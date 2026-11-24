#!/bin/bash
# usage (Git Bash): MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash research_data/locomo_audit_20261123/run.sh <module> [args]
cd /mnt/c/Users/HP/Documents/sdp-locomo-audit
export PYTHONHASHSEED=0 PYTHONPATH=src:.:$HOME/venvs/locomo_overlay OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1
exec ~/venvs/sdp/bin/python -m "$@"
