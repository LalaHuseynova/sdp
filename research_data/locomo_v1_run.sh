#!/bin/bash
# usage (Git Bash): MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash research_data/locomo_v1_run.sh <args...>
cd /mnt/c/Users/HP/Documents/sdp
export PYTHONHASHSEED=0 PYTHONPATH=src:.:$HOME/venvs/locomo_overlay OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
exec ~/venvs/sdp/bin/python "$@"
