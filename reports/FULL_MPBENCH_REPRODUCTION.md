# Original SAFE-Mem: full MPBench reproduction

Prepared 2026-10-28. **Offline preparation is complete; paid execution awaits explicit approval. No new paid LLM calls were made during this audit. Full reproduced scores remain pending.**

This stage covers MPBench's main published comparison, not LoCoMo, EHRAgent, or every supplementary ablation. It introduces no dynamic reputation, new trust propagation, access-policy overlay, new lessons mechanism, or model training.

## Audited protocol and complete dataset

The downloaded files are byte-identical to official [MPBench](https://github.com/Digital-Trust-Lab/mp-bench) commit `6886880a7c29625e0109e0ad91d0e095029f1577`. Both Git blob hashes and SHA256 hashes were checked: [official byte validation](mpbench_official_byte_validation.json), [dataset audit](full_mpbench_dataset_audit.json).

| Quantity | Count |
|---|---:|
| Cases written into the single shared memory pool | 6,240 |
| Attack cases written | 3,241 |
| Benign cases written | 2,999 |
| Attack cases with evaluation questions | 2,999 |
| Benign cases with evaluation questions | 2,997 |
| Total answer rows | 5,996 |
| Benign rows with target annotations | 2,856 |
| Explicit-retention denominator | 249 |
| Suggestive-case restraint denominator | 2,607 |
| Write-only cases retained in memory construction | 244 |

Thus **6,240 is the number of source cases ingested, not a fixed number of extracted claims**. The original extractor determines how many claims each case creates. There is no new training/test partition: every method sees the same complete pool and original questions, categories, payloads, shuffle seed, and scoring labels.

The scored attack categories are repetition 600, explicit keyword 599, delayed conditional 599, fact injection 601, and experience injection 600. The other 242 attack inputs remain in the pool. Two benign inputs also lack retrieval questions; 141 other benign questions lack target annotations and do not enter benign utility scores.

The adversarial file has 3,240 nonempty lines but 3,241 JSON objects, because one line contains two objects. The original tolerant loader handles this. A separate strict stream check consumed the entire file; counting lines would undercount it.

The official files reuse **300 original IDs across splits**. Internal keys are now `adversarial:<original_id>` and `benign:<original_id>`. Every raw dictionary, ID, file byte, payload, label, and record order is preserved. This prevents pooled bookkeeping from overwriting one split with the other. The split tags stay in evaluation bookkeeping; they are not added to model prompts.

## Original method fidelity and necessary changes

Upstream SAFE-Mem checkout: `bac6090985647d7aeff3b44da68e528607a89e0f`. The preflight compared **67 tracked memory, core governance, baseline, prompt, and source-configuration files against HEAD: all unchanged**. See [preflight record](full_mpbench_preflight.json).

| Change | Reason and scope |
|---|---|
| OpenRouter transport and environment-resolved model selection | All paid chat roles use OpenRouter. Default model names match the paper; no model fallback is configured. This changes transport, not method prompts or governance. |
| Explicit `pool_size: 6240` for every method | Upstream `configs/mpbench.yaml` omits this setting and otherwise defaults to one case per store. The paper and author result paths specify a shared 6,240-case pool. |
| Split-qualified internal case IDs | Corrects the official cross-file identifier overlap without editing or removing data. |
| Full-run validation and additional saved fields | Saves every ingestion, original/internal IDs, before/after filtering text, answers with/without memory, and available judge reasons. It adds no model calls and preserves original verdict computation and call order. |
| GPT-5.6-terra OpenRouter price entry | Prevents its usage from being silently treated as unpriced/zero. Prices are estimates, not billing statements. |
| Separate offline comparison analysis | Preserves the original summary and adds the released 2,000-resample query-clustered ASR bootstrap for comparison with the paper. |

The prepared SAFE-Mem arm retains sentence-level endorsement, five authority levels, scope checks, conflict detection, withhold mode, four claims plus four admissible evidence passages, zero graph hops, original prompt versions, and local all-MiniLM-L6-v2 embeddings. Simple Memory retains the original extraction and answer prompts, up to six facts per write, and four retrieved facts. Different original prompts across methods remain different.

The default worker count is **16**, matching the four original backbone presets. `SAFE_MEM_WORKERS` can explicitly override this operational setting; the resolved value is recorded. Weights, selected third-party code, embedding-cache artifacts, prompts, source code, raw data, and generated configurations are hashed or revision-recorded. The launcher checks these before execution.

## Models and environment variables

| Paper backbone | OpenRouter model for memory and answering | Environment variable |
|---|---|---|
| GPT-4o-mini | `openai/gpt-4o-mini` | `SAFE_MEM_MODEL_4OMINI` |
| GPT-5.6-terra | `openai/gpt-5.6-terra` | `SAFE_MEM_MODEL_GPT56` |
| Claude Haiku 5.5 | `anthropic/claude-haiku-5.5` | `SAFE_MEM_MODEL_HAIKU55` |
| Qwen3.8-Flash | `qwen/qwen3.8-flash` | `SAFE_MEM_MODEL_QWEN38FLASH` |

The common judge is `openai/gpt-4o-mini`, selected by `SAFE_MEM_JUDGE_MODEL`. The key remains `OPENROUTER_API_KEY` in the repository-root `.env`. `.env.example` documents the non-secret model variables. For a single selected backbone, `SAFE_MEM_MEMORY_MODEL` and `SAFE_MEM_AGENT_MODEL` can override the two roles separately.

Model values are resolved into YAML during preparation, rather than changing original configuration parsing. Intentional substitutions are declared in `reproduction.model_substitution` and require a matching saved price catalog. Their completed results are labeled **full coverage with model substitution**, not faithful same-model reproductions. The current 32-job plan has **zero model substitutions**.

Reasoning is disabled for the non-mini backbones, matching the original backbone presets. GPT-4o-mini has already passed live OpenRouter integration checks in the earlier bounded run. Other backbones have passed offline configuration checks and public availability checks; their live compatibility checks can occur only after paid approval. Public availability does not guarantee identical provider behavior.

The paper's general temperature-zero description has an upstream exception: its A-MemGuard adapter requests temperature 1.0. That existing behavior is preserved and documented, not silently changed.

## Published baselines and their exact scope

The prepared matrix contains eight methods on four backbones, **32 complete-dataset jobs**:

1. Simple Memory / no defense.
2. Original SAFE-Mem v3.1 withhold.
3. A-MemGuard, using the original SAFE-Mem comparison's consensus-only wrapper.
4. DRIFT Injection Isolator only.
5. RandEC local DistilBERT suffix classifier.
6. LLM sanitizer.
7. MemLineage coarse-attribution adapter.
8. The strict `integrity_gate_all` implementation labeled TMA-NM by the paper-generation code.

These reproduce the SAFE-Mem comparison's operationalizations. They do not imply full reproductions of every feature in the other defenses' own papers. In particular, no additional A-MemGuard lessons mechanism is added. The upstream-monitor TMA-NM strict/values variants are separate appendix experiments and are not silently substituted for the main-table proxy. See [baseline readiness](MPBENCH_BASELINE_READINESS.md) and [paper protocol audit](MPBENCH_PAPER_PROTOCOL.md).

## Metrics and published comparison

| Metric | Numerator / denominator |
|---|---|
| End-to-end ASR | Attack answers that endorse or act on the injected target / 2,999. Mere reporting of artifact content is excluded by the original judge. |
| Retention Recall | Explicit-retention answers using the retained target / 249. |
| Restraint | Suggestive benign answers avoiding assertion of the suggested user claim / 2,607. |
| Combined benign utility, supplemental | Correctly handled annotated benign cases / 2,856. This combines retention and restraint; it is not general task QA accuracy. |
| Missed retention, supplemental | 1 minus Recall, with the same 249-case denominator. |
| Unwanted assertion, supplemental | 1 minus Restraint, with the same 2,607-case denominator. |

There is no complete gold unsafe label for every extracted or retrieved claim in this pooled setting. We therefore do not call case-level flag rates classifier FPR/FNR, do not rename ASR as FNR, and do not substitute classification accuracy for answer behavior.

The original runner's Wilson intervals remain in its summary. The supplemental analyzer uses the released query-cluster bootstrap with 2,000 resamples and seed zero. It requires exact question coverage, matching hashes/settings/models, all 6,240 actual write-log rows, one pool, nonempty answers, and the original metric denominators before assigning a full-result status. It reports recorded answer-judge fallbacks without changing the original verdicts.

Published GPT-4o-mini targets from Table 1 are shown below; the right column remains pending:

| Method | Published ASR / Recall / Restraint (%) | Reproduced full result |
|---|---|---|
| Simple Memory | 49.8 / 79.5 / 36.5 | Pending approval and execution |
| SAFE-Mem | 6.2 / 85.9 / 50.6 | Pending approval and execution |

The [complete 32-row comparison](full_mpbench_analysis/comparison.md) and [machine-readable targets](mpbench_published_targets.json) are prepared. Earlier 80-case scores are excluded. In particular, an earlier result-directory name containing `pool6240` only recorded the configured pool capacity: `--limit 80` had reduced that run to 80 source cases. It was not a 6,240-ingestion experiment.

## Offline checks completed

- The complete official data loads with the expected counts; 300 cross-split IDs are safely distinguished and raw hashes are unchanged.
- A full lifecycle rehearsal with scripted memory/judge/answer functions observed every one of 6,240 writes and all 5,996 read outcomes. It produced no benchmark-performance claims.
- **42 offline tests passed**, covering data identity, full ingestion, original call order, baseline wiring, real cached MiniLM/RandEC loading, metric calculations, incomplete-result rejection, price accounting, and approval/budget guards. [Test log](full_mpbench_offline_tests.log).
- Main environment: 67 compatible packages; MINJA environment: 66 compatible packages. Locked `uv sync --dry-run` proposes no changes. MINJA is not needed for this MPBench run.
- Ruff checks and formatting passed; `git diff --check` passed.
- The default full launcher was run in offline review mode only. [Review log](full_mpbench_offline_plan_review.log).

## Costed approval scopes

Estimates use the unauthenticated [OpenRouter model catalog](https://openrouter.ai/api/v1/models), saved on 2026-10-28, prior GPT-4o-mini stage-token measurements, exact full-dataset counts, and explicit assumptions for unrun baseline overhead. They exclude local embedding operations from paid counts and include the original judges and no-memory controls.

| Approval scope | Jobs | Typical logical chat requests, before cache savings | Typical token cost | Conservative planning cost |
|---|---:|---:|---:|---:|
| A: GPT-4o-mini Simple Memory + SAFE-Mem | 2 | 75,657 | $7.18 | $23.17 |
| B: GPT-4o-mini, all eight methods | 8 | 325,977 | $34.32 | $110.38 |
| C: All eight methods on all four backbones | 32 | 1,303,908 | $595.55 | $2,173.81 |

Every scope uses the complete dataset. A and B are explicitly narrower method/backbone stages, not completion of the four-backbone comparison. The remaining rows stay pending until approved and executed.

These are planning scenarios, not statistical confidence intervals or guaranteed billing caps. They assume no cache discounts across jobs; the shared cache may substantially reduce calls and expense. Conversely, longer completions, concurrent cache misses, retries, credit fees, and taxes can change the total. The original DRIFT and A-MemGuard output caps permit larger costs than the conservative scenario. Detailed assumptions and per-job costs: [cost estimate](full_mpbench_reproduction/cost_estimate.md), [JSON](full_mpbench_reproduction/cost_estimate.json).

The launcher monitors uncached provider usage against an explicitly approved estimated-cost threshold, stops before launching another job once reached, and records incomplete jobs without scores. This monitor uses ledger estimates; in-flight requests, failed requests missing from the original ledger, and billing fees mean it is not an OpenRouter-side hard spending cap. If the approved budget is exhausted, the remaining evaluation stays incomplete until further approval.

## Reproducible commands

Preparation and review below make no LLM requests:

```bash
.venv/bin/python scripts/prepare_full_mpbench.py
.venv/bin/python scripts/run_full_mpbench.py

# Optional: prepare a separate plan for one published backbone.
.venv/bin/python scripts/prepare_full_mpbench.py \
  --backbones 4omini --output-dir reports/mpbench_4omini_plan

HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  .venv/bin/python -m unittest discover -s tests -p '*mpbench*.py' -v
```

The frozen default plan is [plan.json](full_mpbench_reproduction/plan.json); its 32 resolved configurations are in `reports/full_mpbench_reproduction/configs/`. Changing code, raw data, selected local artifacts, or a resolved configuration invalidates the existing plan; regenerate and review it before execution.

Only after explicit approval, an example for scope A with a $25 total estimated-cost threshold is:

```bash
.venv/bin/python scripts/run_full_mpbench.py \
  --jobs 4omini/no_defence,4omini/safe_mem \
  --execute --approved-budget-usd 25 \
  --approval-note 'Scope A and threshold explicitly approved by the user'
```

For scope B, select the eight `4omini/...` job IDs. For scope C, omit `--jobs`. Supply the actually approved threshold and approval note; these examples do not constitute approval. All jobs invoke the original runner with `--require-full --yes`, a 6,240 pool, and no subset flag.

Jobs run sequentially, with the original configured concurrency within each job. A dedicated shared cache is at `reports/full_mpbench_reproduction/cache/responses.sqlite`; it starts independently of earlier smoke caches. Completed jobs are revalidated and skipped on continuation. An interrupted job can replay successful requests from this cache; a cached malformed/empty response must be audited rather than silently changing prompts or generation settings.

Outputs are saved beneath `results/full_mpbench_reproduction/<plan-hash>/<backbone>/<method>/`. Each completed run contains original summaries, outcomes, usage ledger, resolved configuration/prompt manifest, case catalog, dataset hashes, and one write-log row per ingestion, including empty writes. The enclosing execution record and sanitized console log preserve progress, errors, validation, and estimated expense.

After approved runs finish, regenerate the comparison using their actual result-directory paths:

```bash
.venv/bin/python scripts/analyse_mpbench_reproduction.py \
  --run 4omini no_defence results/ACTUAL_FULL_SIMPLE_DIRECTORY \
  --run 4omini safe_mem results/ACTUAL_FULL_SAFE_MEM_DIRECTORY
```

## Limits to exact numerical agreement

Using the same public model names through another provider does not establish identical backend revisions or routing. The current dependency lock and local embedding snapshot are recorded, but a historical author environment and model snapshot are not fully specified. These differences, stochastic generation, the documented upstream ID correction, and baseline operationalization ambiguities may affect agreement; they must be reported rather than hidden or tuned against the paper's numbers.

One paper/data discrepancy remains: Appendix J reports 2,893 distinct attack questions; the validated official release contains 2,891 distinct exact strings among the same 2,999 scored attacks. We preserve all strings and use the actual groups in the released bootstrap procedure. No data is changed to force that count.

Full-dataset execution and the reproduced-vs-published analysis remain pending approval. Preparation, old subset results, and scripted offline checks are never labeled a full numerical reproduction.
