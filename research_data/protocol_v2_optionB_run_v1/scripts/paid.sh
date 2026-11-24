#!/bin/sh
# Paid steps of the option-B runbook (owner-approved 15 Nov 2026). Usage: paid.sh PB1|PB2|PB3|PB4
set -u
cd /Users/ulkerhuseynova/Desktop/SAFE-Mem
export VIRTUAL_ENV=
OPENROUTER_API_KEY=$(grep '^OPENROUTER_API_KEY=' .env | head -1 | cut -d= -f2- | tr -d '"'"'"' ')
export OPENROUTER_API_KEY
FZ=research_data/protocol_v2_freeze_optionB_20261115
RUN=research_data/protocol_v2_optionB_run_v1
B=research_data/controlled_workload_v4_20261108
S=research_data/controlled_workload_stage1_test_v4_20261108
# Rerun 1 (owner, 17 Nov 2026, option 1): the first P-B2 halted on an unknown-billing receipt (Mac slept mid-call),
# which blocks sessions/v2_stage3 by design. Fresh sessions and outputs; sessions/, gpt/, conflict_replies.json kept as the record.
# Rerun 2 (owner, 17 Nov 2026): rerun 1 halted on a network drop (APIConnectionError, unknown billing); sessions_rerun1/, gpt_rerun1/ kept.
# Rerun 3 (owner, 17 Nov 2026): rerun 2 halted the same way on home Wi-Fi; sessions_rerun2/, gpt_rerun2/ kept.
# Freeze revision 6: never-connected attempts are retried inside the same call (protocol §15).
# Freeze revision 7 (owner, 19 Nov 2026): reviewed unknown transport failures booked at worst case and re-sent (protocol §15).
# Freeze revision 8 (owner, 21 Nov 2026): Haiku answers sent without temperature (endpoints refuse it); 404 reviewable (protocol §15).
# Freeze revision 9 (owner, 21 Nov 2026): Haiku answers sent with reasoning disabled (it used up the 200-token limit).
SESS=$RUN/sessions_rerun3
COMMON="--sessions $SESS --approval $FZ/owner_approval_optionB_rev9.json --freeze $FZ/protocol_v2_optionB_rev9.json --confirm-paid"
case "$1" in
  PB1) uv run python scripts/run_protocol_v2.py conflicts --bundle $B \
         --requests $RUN/precompute/G-T*/conflict_requests.json --out $RUN/conflict_replies_rerun3.json $COMMON ;;
  PB2) uv run python scripts/run_protocol_v2.py paid --bundle $B --stage1 $S --out $RUN/gpt_rerun3 \
         --contexts $RUN/contexts/G-T?? $COMMON ;;
  PB3) uv run python scripts/run_protocol_v2.py paid --bundle $B --stage1 $S --out $RUN/haiku --backbone haiku \
         --cells localized distributed sybil_k4 sybilown_k4 launder_r4 launder_r3_rand sybilown_k4_rand imp_localized_fp1 \
         --methods static R C M a_memguard memlineage llm_sanitiser randec S SL S2-ID $COMMON ;;
  # Revision 10 (owner, 23 Nov 2026; post hoc): Gemini 3.1 Flash-Lite, third answering backbone, the same 8 cells and
  # 11 methods as P-B3. Revision 11 (23 Nov): 429 retry + Gemini pacing; resumes under freeze/approval rev11.
  PB4) uv run python scripts/run_protocol_v2.py paid --bundle $B --stage1 $S --out $RUN/gemini --backbone gemini \
         --cells localized distributed sybil_k4 sybilown_k4 launder_r4 launder_r3_rand sybilown_k4_rand imp_localized_fp1 \
         --methods static R C M a_memguard memlineage llm_sanitiser randec S SL S2-ID \
         --sessions $SESS --approval $FZ/owner_approval_optionB_rev11.json --freeze $FZ/protocol_v2_optionB_rev11.json \
         --confirm-paid ;;
  *) echo "usage: paid.sh PB1|PB2|PB3|PB4"; exit 2 ;;
esac
