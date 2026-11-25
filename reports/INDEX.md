# Reports index: start here (25 Nov 2026)

This folder mixes current documents with history from earlier project phases.

The old files are **kept at their original paths on purpose**:
- the frozen integrity snapshot (`research_data/archive_pre_protocol_v2_20261113/file_hashes.jsonl`, checked in the Option B RUNBOOK) records their paths;
- older research code reads or hashes some of them;
- frozen documents link to them.

Do not move or edit them. Use this index instead.

## 1. Current: read these

### MPBench Option B (the main experiment)

| File | What it is |
|---|---|
| [PROTOCOL_V2_OPTION_B_20261115.md](PROTOCOL_V2_OPTION_B_20261115.md) | The frozen protocol of the main experiment |
| [CONTROLLED_WORKLOAD_20261108_SPEC.md](CONTROLLED_WORKLOAD_20261108_SPEC.md) | The controlled MPBench workload: groups, contributions, audits |
| [WORKLOAD_AUDIT_FREEZE_20261108_REPORT.md](WORKLOAD_AUDIT_FREEZE_20261108_REPORT.md), [LOCKED_TEST_V4_20261108_REPORT.md](LOCKED_TEST_V4_20261108_REPORT.md) | Workload freeze and the v4 test split |
| [WHY_GENERATED_DATASET_20261114.md](WHY_GENERATED_DATASET_20261114.md) | Why a generated workload was needed |
| [COST_ESTIMATE_V2_20261114.md](COST_ESTIMATE_V2_20261114.md) | Protocol v2 cost estimate |
| [PROTOCOL_V2_DRAFT_20261113.md](PROTOCOL_V2_DRAFT_20261113.md) | The full v5 plan (future confirmatory run) |
| [JUDGE_VALIDATION_GUIDELINES_V2_DRAFT.md](JUDGE_VALIDATION_GUIDELINES_V2_DRAFT.md) | Judge-validation guidelines |
| `../research_data/protocol_v2_optionB_run_v1/paper_tables/` | Results tables, figure and PDF (GPT-4o-mini, Claude Haiku, Gemini) |

### How the workload and S were designed (dev evidence)

- `CONTROLLED_WORKLOAD_*_20261108_REPORT.md` (5 files)
- [PROPAGATION_FEASIBILITY_20261108_REPORT.md](PROPAGATION_FEASIBILITY_20261108_REPORT.md)
- [ATTACK_CARRIER_DIAGNOSTIC_20261107_REPORT.md](ATTACK_CARRIER_DIAGNOSTIC_20261107_REPORT.md)
- [SV2_CANDIDATES_DEV_20261112_REPORT.md](SV2_CANDIDATES_DEV_20261112_REPORT.md)
- [ADAPTIVE_ATTACKS_DEV_EXPOSURE_20261112_REPORT.md](ADAPTIVE_ATTACKS_DEV_EXPOSURE_20261112_REPORT.md)
- [PUBLISHED_BASELINES_SWEEP_DEV_EXPOSURE_20261112_REPORT.md](PUBLISHED_BASELINES_SWEEP_DEV_EXPOSURE_20261112_REPORT.md)

### Reproducing original SAFE-Mem on MPBench

- [FULL_MPBENCH_REPRODUCTION.md](FULL_MPBENCH_REPRODUCTION.md)
- [OPENROUTER_REPRODUCTION.md](OPENROUTER_REPRODUCTION.md)
- [MPBENCH_PAPER_PROTOCOL.md](MPBENCH_PAPER_PROTOCOL.md) (audit of the original MPBench protocol)
- [MPBENCH_BASELINE_READINESS.md](MPBENCH_BASELINE_READINESS.md)
- `safemem_full_mpbench/` (run report, cost accounting, validation audits, metrics)
- `full_mpbench_analysis/`, `full_mpbench_reproduction/`, [full_mpbench_cost_estimate.md](full_mpbench_cost_estimate.md)

### Audits and reviews

| File | What it is |
|---|---|
| [RESEARCH_AUDIT_20261124.md](RESEARCH_AUDIT_20261124.md) | Full critical research audit (24 Nov) |
| [COST_AUDIT_OPTION_A_20261125.md](COST_AUDIT_OPTION_A_20261125.md) | MPBench vs LoCoMo Option A cost audit |
| [ICML_CRITICAL_REVIEW_20261122.md](ICML_CRITICAL_REVIEW_20261122.md), [ICML_AUDIT_MPBENCH_S2ID_LOCOMO_20261123.md](ICML_AUDIT_MPBENCH_S2ID_LOCOMO_20261123.md) | ICML-style reviews |

### LoCoMo and benchmark choice

- `PROTOCOL_LOCOMO_*.md`
- `LOCOMO_*.md`
- [SAFE-Mem_LoCoMo_results_tables_20261124.pdf](SAFE-Mem_LoCoMo_results_tables_20261124.pdf)
- [BENCHMARKS_AND_MODELS_SURVEY_20261123.md](BENCHMARKS_AND_MODELS_SURVEY_20261123.md)
- [MEM_INV_BENCH_FEASIBILITY_20261123.md](MEM_INV_BENCH_FEASIBILITY_20261123.md)

The LoCoMo code lives on branch `locomo-backup`.

### Method explanations (good for new teammates)

- [DEFENSE_METHODS_EXPLAINED_20261122.pdf](DEFENSE_METHODS_EXPLAINED_20261122.pdf) (+ .html)
- [SAFE_MEM_S_SL_S2ID_METHODS_20261122.pdf](SAFE_MEM_S_SL_S2ID_METHODS_20261122.pdf) (+ .html)
- [MEMLINEAGE_RANDEC_SLIDES_20261122.pptx](MEMLINEAGE_RANDEC_SLIDES_20261122.pptx)

### Setup

- [SETUP.md](SETUP.md)
- [README.md](README.md) (the report guide as of 7 Nov)

## 2. Outdated: history only (do not use for current work)

| File | Why it is outdated |
|---|---|
| `SAFE_MEM_VS_S_PRESENTATION_20261115.html` | Early presentation (15 Nov) |
| `TABLE_PREVIEW_V2_20261115.md` | Table preview, replaced by protocol §9 and `paper_tables/` |

**Before protocol v2 (29 Oct – 7 Nov 2026):** these phases used an earlier design that protocol v2 replaced.

| Group | Files |
|---|---|
| Phases | `PROVISIONAL_*`, `PILOT_FINISH_*`, `STEP_9/10/11_*`, `STEPS_7_8_*`, `RECOVERY_*`, `NATIVE_STORES_*`, `API_EXECUTION_*`, `DYNAMIC_COMPARISON_*` |
| Review and calibration | `LLM_REVIEW_*`, `LLM_EXPLORATORY_PROTOCOL_*`, `AI_PILOT_ADJUDICATION_*`, `QUESTION_CHECKER_CALIBRATION_*`, `SPAN_REVIEWER_*`, `UTILITY_QUESTION_REVIEW_*`, `SCOPED_COHORT_*`, `FOCUSED_REVIEW_WORKFLOW_*` |
| Early planning | `PHASE1_*`, `FIRST_EXPERIMENT_PROTOCOL.md`, `DEFENSE_IMPLEMENTATION_PLAN.md`, `MPBENCH_DYNAMIC_EXPERIMENT_PROTOCOL.md`, `RESEARCH_PROPOSAL*.md`, `STRICT_BUDGET_DESIGN_REVIEW.md` |
| Old reviews | `RESEARCH_AUDIT_20261101_REPORT.md`, `REPOSITORY_REVIEW_20261107.md` |
| Housekeeping records | `CLEANUP_AUDIT_20261115.md`, `CLEANUP_AUDIT_20261121.md` (referenced by the Option B RUNBOOK) |
