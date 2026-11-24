#!/bin/bash
# Free LoCoMo v2 pipeline: build (3 parallel workers) -> tests -> estimate -> dev mechanism -> full mock -> freeze prepare.
cd /mnt/c/Users/HP/Documents/sdp-locomo-audit
R=research_data/locomo_v2
run() { bash $R/run.sh "$@"; }
set -o pipefail
run -m locomo_v2 build --randec --convs conv-26 conv-30 conv-41 conv-42 > $R/build_a.log 2>&1 &
run -m locomo_v2 build --randec --convs conv-43 conv-44 conv-47 > $R/build_b.log 2>&1 &
run -m locomo_v2 build --randec --convs conv-48 conv-49 conv-50 > $R/build_c.log 2>&1 &
wait || exit 2
grep -h '"conv"' $R/build_?.log > $R/build_summary.jsonl
run -m pytest -q locomo_v1/tests locomo_audit/tests locomo_v2/tests > $R/tests.log 2>&1 || exit 3
run -m locomo_v2 estimate > $R/estimate.json 2>/dev/null || exit 4
run -m locomo_v2 mechanism --convs conv-48 conv-49 > /dev/null 2>&1 || exit 5
run -m locomo_v2 mock --run $R/mock > $R/mock.log 2>&1 || exit 6
run -m locomo_v2 freeze prepare > $R/freeze_prepare.log 2>&1 || exit 7
run -m locomo_v2 freeze verify > $R/freeze_verify.log 2>&1 || exit 8
echo PIPELINE_OK
