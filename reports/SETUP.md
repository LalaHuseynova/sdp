# SAFE-Mem local setup

Prepared on 2026-10-28 for this Mac, using Python 3.11.

## Installed environments

- Main experiments: `.venv/`. Includes local embeddings, LoCoMo scoring, analysis tools, and development dependencies.
- EHRAgent/MINJA: `.venv-minja/`. Keeps AutoGen 0.2.0, OpenAI 1.7.2, and HTTPX 0.27.2 separate from the main environment.
- Exact installed packages: `reports/main-environment.txt` and `reports/minja-environment.txt`.
- The main `uv.lock` was refreshed during installation. A subsequent locked dry run reports no changes needed.

## Downloaded assets

| Asset | Local location |
|---|---|
| MPBench, 3,241 attack and 2,999 benign cases | `data/mpbench/` |
| LoCoMo, 10 conversations and 1,540 non-adversarial questions | `data/locomo/locomo10.json` |
| LongMemEval-S, 500 questions | `data/longmemeval/longmemeval_s_cleaned.json` |
| MIMIC-III Clinical Database Demo v1.4 | `data/mimic-iii-clinical-database-demo-1.4/` |
| Prepared EHRAgent demo database, 100 patients and 129 admissions | `third_party/MINJA/EHR/ehragent/ehrsql-ehragent/mimic_iii/` |
| MINJA including EHRAgent | `third_party/MINJA/` |
| A-MemGuard | `third_party/AMemGuard/` |
| TMA-NM | `third_party/mem-inv-bench/` |
| RandEC DistilBERT weights, suffix/insertion/infusion | `third_party/AMemGuard/certified-llm-safety/models/` |
| MiniLM and base DistilBERT models/tokenizers | Hugging Face cache under `~/.cache/huggingface/hub/` |

Upstream repositories were checked out at the commits specified by `scripts/fetch_third_party.sh`. MINJA's full EHR Git LFS objects were skipped; the paper uses the open-access MIMIC demo instead. The repository's MINJA compatibility patch was applied.

Sources, file hashes, and repository commits are recorded in `reports/download_manifest.json`. Model cache paths are recorded in `reports/model_cache.json`.

## Run a first experiment

OpenRouter is now configured using `OPENROUTER_API_KEY` in `.env`. The credential was originally stored under `OPENAI_API_KEY`; its variable name was corrected without displaying the value. `.env.example` shows the supported variable names without credentials.

From the project root:

```bash
.venv/bin/python scripts/run_mpbench.py \
  --config configs/v31_mpbench_withhold.yaml \
  --backbone openrouter_4omini --limit 80
```

The `openrouter_4omini` backbone sends memory, agent, and judge requests to GPT-4o-mini through OpenRouter. It uses local MiniLM embeddings and has no author-specific fallback. Other upstream backbone presets retain their original provider settings.

To repeat the live governance integration check:

```bash
.venv/bin/python scripts/verify_openrouter.py
```

For LoCoMo:

```bash
.venv/bin/python scripts/run_locomo.py \
  --config configs/v31_locomo_withhold_a.yaml \
  --backbone openrouter_4omini --limit 1 --yes
```

For EHRAgent/MINJA, use its separate environment:

```bash
source .venv-minja/bin/activate
export AMS_PY="$PWD/.venv/bin/python"
export BACKBONE=openrouter_4omini
bash scripts/server_minja_demo.sh \
  "$PWD/data/mimic-iii-clinical-database-demo-1.4"
```

These experiment commands make paid LLM calls when responses are not already cached. OpenRouter smoke runs are recorded in `results/` and summarized in `reports/OPENROUTER_REPRODUCTION.md`; full-dataset paper experiments remain separate from the smoke runs.

## Checks performed

- Main and MINJA dependency compatibility checks.
- MPBench, LoCoMo, and LongMemEval-S parsing through the project's own loaders.
- All 27 published MIMIC demo file checksums, followed by conversion to EHRAgent's tables and a successful SQLite integrity check. The demo is installed at EHRAgent's expected data path and marked with `.demo`, so the runner reuses it.
- Main experiment command-line entry points.
- AutoGen/OpenAI imports and client construction in the MINJA environment.
- MiniLM embedding generation in both environments, including an offline MINJA check.
- RandEC classifier initialization with downloaded weights and classification of a benign sentence.
- TMA-NM import from its pinned upstream implementation.
- A local SAFE-Mem write/retrieve check using scripted claim extraction and actual MiniLM embeddings: authorized preferences are retrieved, external approvals are withheld from preference use, another principal cannot inherit those preferences, and external claims remain reportable. Details are in `reports/governance_smoke.json`.

The complete setup summary is in `reports/setup_status.json`.
