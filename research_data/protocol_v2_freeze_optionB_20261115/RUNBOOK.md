# Option B runbook: exact commands, order, caps (protocol v2, revision 5)

Protocol: `reports/PROTOCOL_V2_OPTION_B_20261115.md`. Freeze manifest: `protocol_v2_optionB.json` (this folder), digest `1845a84d73b1961201dd63884e43807f363ed89b08a84662b2d1fb43922e4903`.

**Nothing here may be run until the owner has signed the approval file** (`owner_approval_optionB.json`, made from `owner_approval_optionB.DRAFT.json` by the owner). Every paid command refuses to run without `--confirm-paid`, an approval with `approved_by: owner` naming the digest above, a verifying freeze manifest, the frozen dataset, and `PYTHONHASHSEED=0` (the scripts set it themselves).

## 0. Setup (every step)

```bash
cd ~/Desktop/SAFE-Mem
export VIRTUAL_ENV=
FZ=research_data/protocol_v2_freeze_optionB_20261115
FREEZE=$FZ/protocol_v2_optionB.json
APPROVAL=$FZ/owner_approval_optionB.json          # the owner's signed copy of the DRAFT
BUNDLE=research_data/controlled_workload_v4_20261108
STAGE1=research_data/controlled_workload_stage1_test_v4_20261108
RUN=research_data/protocol_v2_optionB_run_v1        # new directory; never reused
GROUPS=$(printf "G-T%02d " $(seq 0 23))
```

Paid steps also need `OPENROUTER_API_KEY` in the environment. Run long steps in the foreground (background jobs were about 10× slower on this Mac), the paid ones under `caffeinate -i`.

## 1. Integrity checks (free; before every paid step)

```bash
uv run python scripts/freeze_protocol_v2.py verify --protocol $FREEZE
uv run python scripts/archive_locked_protocol.py verify --protocol research_data/workload_freeze_v4_20261108/locked_protocol_v1.json
uv run python scripts/archive_snapshot.py verify --out research_data/archive_pre_protocol_v2_20261113
```

Expected: `verified`; `verified` (224 files); `differs` with `changed: 0, missing: 3`. The 3 missing files are the approved 15 Nov cleanup (the RandEC zip, deleted after its weights were verified; the two v1 SQLite journals, archived with verified SHA-256 restores; `reports/CLEANUP_AUDIT_20261115.md` §6).

**Update 21 Nov 2026 (owner-approved cleanup after P-B2):** expected snapshot result is now `differs` with `changed: 0, missing: 25` (the 3 above + 22 files of 4 deleted dry-run/mock folders, each listed with SHA-256 in `research_data/cleanup_20261121/deleted_files_sha256.txt`; `reports/CLEANUP_AUDIT_20261121.md`).

## 2. Free precompute (step 1 of Fix 2): conflict-check requests

```bash
mkdir -p $RUN/precompute
printf "%s\n" $GROUPS | xargs -P 4 -I{} uv run python scripts/run_protocol_v2.py precompute \
  --bundle $BUNDLE --stage1 $STAGE1 --groups {} --out $RUN/precompute/{} \
  --methods static R C M S SL S2-BS
```

- About 2 CPU-hours per group; 4 parallel shards ≈ 12 h wall (use `-P 3` if memory is tight; the Mac has 8 GB).
- Writes `$RUN/precompute/G-Txx/conflict_requests.json`. Count them before step 3: `cat $RUN/precompute/*/conflict_requests.json | python3 -c "import json,sys; print(sum(len(json.loads(l)) for l in sys.stdin))"` (dev: ≈ 2.75 per group, so ≈ 66).
- These journals hold retrieval exposure only (no answers). They are not inspected before the analysis.

## 3. PAID P-B1: conflict pass (GPT-4o-mini, `v2_stage3`)

```bash
caffeinate -i uv run python scripts/run_protocol_v2.py conflicts --bundle $BUNDLE \
  --requests $RUN/precompute/G-T*/conflict_requests.json \
  --sessions $RUN/sessions --approval $APPROVAL --freeze $FREEZE \
  --out $RUN/conflict_replies.json --confirm-paid
```

Sends only the recorded 6-token conflict checks; prints the count and the spend.

## 4. Free contexts (step 2 of Fix 2)

```bash
mkdir -p $RUN/contexts
printf "%s\n" $GROUPS | xargs -P 4 -I{} uv run python scripts/run_protocol_v2.py contexts \
  --bundle $BUNDLE --stage1 $STAGE1 --replies $RUN/conflict_replies.json \
  --groups {} --out $RUN/contexts/{}
```

About 2 CPU-hours per group (≈ 12 h wall); ≈ 2.2 GB of contexts in total.

## 5. PAID P-B2: GPT-4o-mini evaluation (all 62 cells × 16 methods)

```bash
caffeinate -i uv run python scripts/run_protocol_v2.py paid --bundle $BUNDLE --stage1 $STAGE1 \
  --out $RUN/gpt --sessions $RUN/sessions --approval $APPROVAL --freeze $FREEZE \
  --contexts $RUN/contexts/G-T* --confirm-paid
```

One process, ≈ 25–54 h. A restart with the same command resumes: completed calls are replayed from the ledger at $0, and every saved row is checked unchanged.

## 6. PAID P-B3: Claude Haiku evaluation (8 cells × 11 methods; judge stays GPT-4o-mini)

```bash
caffeinate -i uv run python scripts/run_protocol_v2.py paid --bundle $BUNDLE --stage1 $STAGE1 \
  --out $RUN/haiku --sessions $RUN/sessions --approval $APPROVAL --freeze $FREEZE \
  --backbone haiku \
  --cells localized distributed sybil_k4 sybilown_k4 launder_r4 launder_r3_rand sybilown_k4_rand imp_localized_fp1 \
  --methods static R C M a_memguard memlineage llm_sanitiser randec S SL S2-ID --confirm-paid
```

Original pipeline path (no `--contexts`). Conflict checks, MemLineage and A-MemGuard requests are exact replays from P-B2's ledger ($0). Rough estimate ≈ 15–30 h (not measured).

## 7. Free analysis (once)

```bash
uv run python scripts/analyse_protocol_v2.py --journal $RUN/gpt --bundle $BUNDLE \
  --label "MPBench v4 split (reused), GPT-4o-mini" \
  --backbone-journal $RUN/haiku --backbone-label "MPBench v4 split (reused), Claude Haiku" \
  --not-run "Fresh v5, GPT-4o-mini" "Fresh v5, Claude Haiku" \
  --evidence replication --mpbench data/mpbench/adversarial_data.jsonl.jsonl \
  --allow-heldout --out $RUN/analysis
```

Writes `analysis.json`, `backbone_analysis.json`, `tables.md` (Tables 1–8), `appendix.md` (A1–A8, A13), `per_cell.md`, figures.

## Spending: estimates and proposed hard caps

Estimates are the step-1.12 dry run (measured dev calls and prices) for 24 groups. **The guard fixes each purpose's cap the first time a stage uses it, and the cap can never change afterwards** (`ConstructionSession.authorize`). P-B1 opens `v2_stage3`, so its cap is set for P-B1, P-B2 and P-B3 together. A cap that is too low would strand the run (a new session would lose the $0 replays). The proposed caps are therefore ≈ 2× the high estimate.

| Paid stage | Purposes it opens | Estimate (low–high) | Hard cap that governs it |
|---|---|---|---|
| **P-B1 conflict pass** | `v2_stage3` | ≈ $0.001 (≈ 66 checks × $0.000016) | `v2_stage3` **$10.00** (shared with P-B2, P-B3); the command can only send the recorded conflict checks |
| P-B2 GPT-4o-mini evaluation | `v2_stage3`, `v2_published_amemguard`, `v2_published_sanitiser`, `v2_published_memlineage` | stage3 $2.31–4.61; A-MemGuard $0.95–2.05; sanitiser $0.12–0.25; MemLineage $0.014 | stage3 $10.00 (shared); A-MemGuard **$4.50**; sanitiser **$0.60**; MemLineage **$0.05** |
| P-B3 Claude Haiku evaluation | all of the above + `v2_backbone_answer` | Haiku answers $0.65–3.52; GPT judges $0.15–0.37 (stage3); published $0 (replayed) | Haiku **$8.00**; stage3 $10.00 (shared) |
| **Total** | | **$4.19–10.82** | **sum of caps $23.15** (allowance left ≈ $26.57) |

Code ceilings (`transport.V2_PURPOSES`): stage3 $80, A-MemGuard $20, sanitiser $10, MemLineage $0.50, Haiku $10. Every proposed cap is below its ceiling. Ablations (stage 6.2, dev data, est. $0.26–1.05) are a separate scope and a separate approval later.

## Disk and time

- Free space now ≈ 9.5 GB. Needed ≈ 4 GB (precompute ≈ 0.9 GB, contexts ≈ 2.2 GB, paid journals ≈ 0.5–1 GB).
- Wall time ≈ 3–5 days in total (12 h + minutes + 12 h + 25–54 h + 15–30 h).
