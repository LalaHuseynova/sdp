# Script guide

Reviewed 7 November 2026. Run scripts from the repository root using the existing `.venv`. This index organizes existing commands; no research implementation was changed during the cleanup.

## Start with read-only/offline checks

```sh
.venv/bin/python scripts/check_research_offline.py -q tests
.venv/bin/python scripts/inspect_research_state.py --out reports/my_new_inspection.json
```

The first blocks networking in the test process. The second validates the dated saved study and recounts outcomes; choose a fresh output path. It deliberately refuses unexpected artifact or budget changes rather than treating them as automatically valid. The known legacy Phase 1 validator problem remains separate.

## Entry points by purpose

| Purpose | Existing scripts | Important boundary |
|---|---|---|
| Original full reproduction | `prepare_full_mpbench.py`, `run_full_mpbench.py`, `analyse_mpbench_reproduction.py` | Execution can make paid calls. The completed original run is a separate result from our defense. |
| Inventory and recovery | `prepare_mpbench_phase1.py`, `prepare_mpbench_recovery.py` | Offline preparation; old regeneration/import paths can encounter the documented fingerprint refusal. |
| Provisional groups/questions | `prepare_mpbench_provisional.py` | Case-intent preparation; not final verified safety-balanced data. |
| Evidence mechanics | `check_dynamic_evidence.py` | Artificial offline fixtures, not research results. |
| Retrieval/restart mechanics | `check_dynamic_retrieval.py`, `check_dynamic_sequence.py` | Artificial offline fixtures with exact replies. |
| Engineering freeze and cost plan | `prepare_dynamic_pilot.py`, `prepare_dynamic_execution.py` | Preparation does not complete scientific validation or start a benchmark. |
| Frozen native stores | `prepare_dynamic_native.py` | Cached construction; no paid fallback for misses. |
| Automated review | `review_mpbench_llm.py`, `review_mpbench_llm_batches.py`, `complete_llm_review.py` | Preparation/checks are offline; explicit run modes can spend API budget. Outputs remain AI proposals. |
| Review follow-ups/quality checks | `review_exact_spans.py`, `resolve_ai_review_items.py`, `recheck_ai_questions.py`, `review_remaining_utility.py`, `recover_ai_question_formatting.py`, `calibrate_question_checker.py`, `validate_question_checker.py`, `confirm_question_checker.py`, `adjudicate_ai_questions.py` | Preserve original failures and versions; these are different stages, not duplicate commands to rerun until a pass. Inspect each CLI before use; some modes are paid. |
| Review accounting and summaries | `analyse_llm_review.py`, `audit_ai_accounting.py`, `audit_ai_preparation.py`, `capture_completed_ai_scope.py` | Check saved work and derived views. |
| Candidate completion/readiness | `finish_ai_pilot.py`, `finish_development_prefix.py`, `finish_development_corrected.py` | Historical orchestration; a completed stage does not mean human validation or final pilot readiness. Some modes may dispatch reviews. |
| Human review / utility scope | `manage_focused_review.py`, `prepare_scoped_cohort.py` | Prepare/import genuine decisions; cannot invent human agreement. |
| Provisional execution preparation | `prepare_provisional_execution.py` | Check matching inputs and readiness before execution. |
| Provisional execution | `run_provisional_comparison.py`, `resume_provisional_comparison.py`, `run_provisional_extension.py` | Paid execution paths use the shared research allowance; a restart is not a new budget. |
| Baseline/admission checks | `check_provisional_baseline.py`, `audit_provisional_admission.py` | Inspect parity and whether external records can actually enter retrieval. |
| Saved-result analysis | `compare_dynamic_results.py`, `summarize_provisional_results.py`, `report_development_comparison.py`, `export_provisional_receipts.py`, `diagnose_provisional_attacks.py` (attack-carrier and S-change diagnostic, 7 Nov), `assess_propagation_feasibility.py` (full-pool propagation feasibility, 8 Nov) |
| Controlled workload (offline) | `generate_controlled_workload.py generate --out <new>` / `check --bundle <dir>` | Generates and validates the 8 Nov controlled workload and its cost estimate. Free; makes no model calls. |
| Controlled workload integration (offline) | `run_controlled_workload.py dry-run --bundle <b> --split dev --out <new>` / `analyse` | Builds SAFE-Mem stores (frozen cache, mock for misses), runs static/R/C/M/S/no-memory with mock answers, analyses the outcomes and writes the exact Stage-1 request audit. Has no paid mode. | Analyze saved outcomes/receipts without inventing missing measurements. |
| Controlled workload Stage 1 / Stage 2 | `stage_controlled_workload.py stage1 --split dev --confirm-paid-dev-stage1` / `stage2 --bundle <b> --stage1 <dir> --out <new>` | Stage 1 is **paid** (owner approval required; dev only; $0.15 hard cap on the shared guarded session; frozen cache first, local MiniLM). Stage 2 is free: extraction yield, classification and retrieval exposure. |
| Controlled workload v2 fact pilot | `pilot_fact_extraction.py plan --bundle <v2> --out <new>` / `run ... --session <dir> --confirm-paid-pilot` | `plan` is free (selection, exact requests, calibrated cost, criteria). `run` is **paid** (owner approval; refuses a blocked session; only planned requests; $0.03 cap). Also: `generate_controlled_workload.py generate --carriers v2`, and the dry-run flags `--mock-extraction request_guided --paid-replay <dispatch.sqlite>`. |
| Controlled workload v3 | `generate_controlled_workload.py generate --carriers v3`; `pilot_fact_extraction.py plan --seed <s> --exclude-from <earlier plan> --replay <dispatch.sqlite>`; `stage_controlled_workload.py stage1 --session <dir> --replay <dispatch.sqlite>` | Fresh-contribution re-pilots, new-session Stage 1, and read-only reuse of paid replies. |
| Controlled workload Stage 3 | `stage_controlled_workload.py stage3 --bundle <v3> --stage1 <dir> --out <dir> --session <dir> (--mock \| --confirm-paid-dev-stage3)` | Answers, conflict checks and judges for static/R/C/M/S/no-memory; resumable journal; paid only with confirmation (dev only, $0.70 cap); `--mock` uses a separate session. |
| Audit and freeze | `generate_controlled_workload.py generate --carriers v4`; `freeze_locked_protocol.py freeze/verify`; `verify_test_untouched.py --out <json>`; `estimate_locked_test_cost.py --bundle <v4> --split test --out <json>` | Final dataset v4, hash-frozen protocol, held-out-test checks and the offline locked-test cost estimate. All free. |
| Table rendering | `render_research_result_tables.py` | Uses saved results; a separate PDF-tool environment is documented in the delivered table README. |

Other scripts include original SAFE-Mem utilities and older LoCoMo/MINJA/baseline work. Their presence is not evidence that every baseline or benchmark was reproduced. Keep them separate from our dynamic-defense claims; use the [original README](../UPSTREAM_README.md) and dated reports for their scope.

## Why similarly named scripts remain

`run_mpbench.py` is the original benchmark runner; `run_full_mpbench.py` adds a checked full-reproduction launcher; `run_provisional_comparison.py` runs our separate research comparison. They are different layers.

Likewise, a preparation command, a validator, a resume command and an analyzer are different operations. Removing one because its name resembles another would remove functionality or break frozen source fingerprints. No redundant nonempty implementations were found within `src/`, `scripts/`, `tests/` and `configs/` by the exact-byte duplicate scan.

Before any new paid run, disclose an estimate and use the existing total allowance. Documentation examples are not a request to rerun completed work.
