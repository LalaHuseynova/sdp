#!/bin/bash
# usage (Git Bash): MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu -- bash research_data/locomo_pilot_20261119/run.sh <mode> <run_dir>
cd /mnt/c/Users/HP/Documents/sdp
export PYTHONHASHSEED=0 PYTHONPATH=src:.:$HOME/venvs/locomo_overlay OMP_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
PY=~/venvs/sdp/bin/python
$PY research_data/locomo_pilot_20261119/pilot.py --mode "$1" --run "$2" > "$2.log" 2>&1
echo "exit $?" >> "$2.log"
if [ "$1" != dry ]; then $PY research_data/locomo_pilot_20261119/analyse.py "$2" >> "$2.log" 2>&1; echo "analyse exit $?" >> "$2.log"; fi
