#!/bin/bash
# free; run from Git Bash: MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash research_data/locomo_feasibility_20261119/run.sh
cd /mnt/c/Users/HP/Documents/sdp
export PYTHONHASHSEED=0 PYTHONPATH=src:. OMP_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
~/venvs/sdp/bin/python research_data/locomo_feasibility_20261119/feasibility.py > research_data/locomo_feasibility_20261119/feasibility.log 2>&1
echo "exit $?" >> research_data/locomo_feasibility_20261119/feasibility.log
