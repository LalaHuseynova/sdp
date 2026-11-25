# MPBench baseline readiness audit

Audited 2026-10-28. All checks described here were offline; paid API calls: **0**. No original memory, governance, baseline, prompt, or scoring implementation was changed by this audit. The new test file supplies scripted LLM replies and loads existing local model weights.

## Published method mapping

The local SAFE-Mem v2 paper, section 5.1 and Table 1, compares eight rows on four backbones. The GPT-4o-mini column is shown below as a reference target, not a reproduced result.

| Paper row | Repository configuration / selector | Implementation actually run | Paper MPBench ASR / Recall / Restraint (%) |
|---|---|---|---|
| No defense | `configs/mpbench.yaml`, `--defences no_defence --pool-size 6240` | `SimpleMemory`: frozen fact extraction plus top-4 embedding retrieval; no additional filter. | 49.8 / 79.5 / 36.5 |
| A-MemGuard | Same config, `--defences a_memguard --pool-size 6240` | Authors' vendored consistency checker: one reasoning chain per retrieved fact, then consensus/safety judgment. The SAFE-Mem adapter implements this component, not an additional defensive lesson store. | 41.0 / 73.5 / 37.3 |
| DRIFT | `configs/mpbench_drift.yaml` | Injection Isolator before extraction; Secure Planner and Dynamic Validator are ablated. | 40.4 / 81.5 / 36.1 |
| RandEC | `configs/mpbench_baselines.yaml`, `--defences randec_distil` | Vendored DistilBERT erase-and-check classifier, suffix mode. | 27.3 / 72.3 / 39.4 |
| LLM sanitizer | Same config, `--defences llm_sanitiser` | Audit each retrieved fact; rewrite only those marked harmful. | 48.2 / 79.5 / 36.4 |
| MemLineage | Same config, `--defences memlineage_coarse` | SAFE-Mem authors' paper-based adaptation: coarse parent attribution, sentinel rendering, and sensitive-request gating. This is not an upstream complete-system installation. | 45.4 / 81.1 / 37.1 |
| TMA-NM | See ambiguity below. | Main artifact includes an unconditional binary integrity gate. A separate adapter runs the authors' monitor in strict/values modes. | 2.4 / 9.6 / 94.7 |
| SAFE-Mem | `configs/v31_mpbench_withhold.yaml` | Original typed standing memory; sentence endorsement, governed retrieval, conflicts, k=4 claims and m=4 passages. | 6.2 / 85.9 / 50.6 |

All configurations must resolve memory/agent models to the selected backbone and judge to GPT-4o-mini through OpenRouter. The paper backbones are GPT-5.6-terra, GPT-4o-mini, Claude Haiku 5.5, and Qwen3.8-Flash. A one-backbone run is a full-dataset reproduction of that column, not of all four columns.

### Important artifact discrepancies

- `configs/mpbench.yaml` does **not** set `pool_size`. The runner defaults to 1, while the paper requires one pool containing all 6,240 writes. The README's main-table command omits the pool override, but `scripts/run_all.sh` supplies it. Explicitly set `--pool-size 6240` for both no defense and A-MemGuard, as well as validating it in every resolved run configuration.
- `src/ams/eval/paper_data.py` maps `integrity_gate[all]` to the display name **TMA-NM** in figure generation, and `scripts/paper_data.py` uses that selector. `src/ams/baselines/integrity_gate.py` calls itself a binary integrity adaptation. Actual upstream-monitor execution is separately available through `configs/mpbench_tma_nm.yaml`, with `tma_nm_strict` and `tma_nm_values`. Appendix G, Table 6, reports strict and values results. Preserve explicit implementation labels; compare the original unconditional gate and upstream strict monitor separately rather than silently claiming they are the same code. Their withholding decisions may agree on many extracted external memories, but that should be verified.
- `memlineage_lm`, `integrity_gate`, `integrity_gate_all`, `tma_nm_values`, and other configurations are extra diagnostic variants. Figure generation selects `memlineage[coarse` for the named MemLineage main row. Do not choose the best post hoc variant as the reproduction.
- The A-MemGuard adapter uses temperature 1.0 and a 2,048-output-token cap, even though the paper gives a general temperature-0 description. This is existing repository behavior. Preserve it and disclose this code/paper discrepancy.
- DRIFT is explicitly the Injection Isolator only. Adding the other DRIFT modules would change the paper comparison.
- The perplexity filter from A-MemGuard's upstream experiments is not in SAFE-Mem Table 1 and is deliberately unsupported by this adaptation because comparable prompt-token likelihoods are unavailable through the selected API. No additional model training is needed.

## Environment and local artifacts

Both dependency checks passed:

```bash
uv pip check --python .venv/bin/python
uv pip check --python .venv-minja/bin/python
```

Main environment: 67 installed packages, all compatible. Separate MINJA environment: 66 packages, all compatible. MPBench uses the main environment; MINJA is not required for its experiment.

Verified offline:

- MiniLM `sentence-transformers/all-MiniLM-L6-v2` loaded from the existing cache and returned a `(1, 384)` embedding.
- RandEC loaded the suffix checkpoint and returned a Boolean verdict. A benign setup probe returned `False`; this is a wiring check, not an estimate of classifier performance.
- All LLM-based baseline constructors accepted an offline provider; no provider credentials or paid connections were used.
- A-MemGuard's LLM method does not require the otherwise-default `all-mpnet-base-v2` download. Its upstream checker loads that model lazily only for clustering.
- TMA-NM's vendored pure-Python monitor imported and its audit-log verification passed in the offline tests.

Pinned upstream trees:

| Artifact | Local revision |
|---|---|
| `third_party/AMemGuard` | `dd92f7ff21b9a904a703141be3d5b80170e57228` |
| `third_party/mem-inv-bench` | `050b2ea5d6560c40f4eec7e8b9afd03e0224d877` |
| MiniLM cached snapshot | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |
| DistilBERT base cached snapshot | `12040accade4e8a0f71eabdb258fecc2e7e948be` |

RandEC checkpoint: `third_party/AMemGuard/certified-llm-safety/models/distilbert_suffix.pt`, 267,862,618 bytes, SHA-256 `57b7536c513da87dc57658b0c0297ce5a6a4a67c57cb219ac9a77b9836c757bc`.

Transformers warns that the base DistilBERT classification head is initially missing; upstream immediately loads the supplied classifier state dictionary. Successful checkpoint loading is the relevant check. This setup does not train that head.

## Offline checks added and executed

[`tests/test_mpbench_baselines_offline.py`](../tests/test_mpbench_baselines_offline.py) contains nine checks. Network socket connections are blocked during the tests and Hugging Face offline mode is enabled. Scripted responses are not performance predictions.

```bash
HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m unittest discover -s tests \
  -p test_mpbench_baselines_offline.py -v

.venv/bin/ruff check tests/test_mpbench_baselines_offline.py
```

Observed result: **9 passed**, 10.613 seconds; Ruff passed. Coverage includes:

1. A-MemGuard upstream consensus accepting/rejecting the intended entries and retaining its original request parameters.
2. Cached MiniLM loading and embedding dimension.
3. Cached RandEC loading and Boolean inference.
4. DRIFT masks before extraction and records the removed span.
5. Conditional and unconditional integrity-gate behavior.
6. MemLineage coarse permits ordinary recall but denies sensitive use with an untrusted ancestor.
7. LM attribution and the original strict-threshold/no-strong-parent fallback behavior.
8. Sanitizer rewriting retains entry identity and provenance metadata.
9. TMA-NM strict/values behavior and monitor-log integrity.

## Approximate uncached call multipliers

These describe logical successful completion requests before cache savings, not a dollar quote or a bound on HTTP attempts. Input lengths, actual output lengths, shared cached requests, empty stores, parallel duplicate cache misses, and retries affect totals. Original runner `projected_calls()` is a rough estimate, not a rigorous upper limit.

The downloaded data has 6,240 writes, 5,996 nonblank retrieval requests: 2,999 attacks and 2,997 benign requests. Of benign requests, 2,856 have annotated memory suitable for the original utility scoring. All 6,240 contexts are nonempty.

For Simple Memory with no filter:

- Each write: one extraction request, output cap 400 tokens.
- Each attack read: at most six requests: written-memory judge, retrieved-memory judge, answer, no-memory answer, and two answer judges. Empty written/retrieved memories skip their entry judge.
- Each benign read: one answer plus one answer judge when annotated memory exists.
- Thus a simple logical request count is at most `6240 + 6*2999 + 2997 + 2856 = 30087` before caching and skipped calls. Rebuilding a store can replay the extraction from cache rather than rebilling it.

| Method | Extra logical completions relative to that substrate | Output caps of extra calls |
|---|---|---|
| A-MemGuard | Up to k+1 = 5 per nonempty read, approximately at most 29,980 additional requests. | 2,048 each. |
| DRIFT Isolator | 1–2 per write with context; up to 12,480 additional requests here. | 10,000 each; actual detected-span replies may be much shorter. |
| RandEC | 0 paid extra calls; CPU classifier inference per retrieved entry plus sampled erasures. | Local only. |
| LLM sanitizer | k audits plus up to k rewrites: at most 8 per read, up to 47,968 additional requests. | 1,024 each. |
| MemLineage coarse | At most one sensitive-action decision per nonempty read. | 4. |
| MemLineage LM | One attribution decision per distinct retrieved entry plus one sensitive-action decision per nonempty read. | 200 per attribution, 4 per sensitivity. |
| Integrity gate sensitive | At most one sensitive-action decision per relevant read. | 4. |
| Integrity gate all | 0 additional paid calls. | None. |
| TMA-NM strict/values | 0 additional paid calls; local monitor work. | None. |
| SAFE-Mem | Replace extraction with retention-sentence classification and one or two claim-extraction passes; add use classification per read and candidate conflict judgments. | Retention `60 + 40 * sentence_count`; extraction 900; use type v2 24; each conflict judge 6. |

Original answer generation is capped at 200 tokens; each original entry/answer judge is capped at 120. The SAFE-Mem conflict-call count depends on extracted predicates and retrieved candidates and cannot be known exactly before model outputs exist. Some no-memory answers differ between the typed and untyped answer prompts, so cross-method cache reuse must not be assumed for every stage.

Use the current OpenRouter model catalog and tokenization of the actual prompts for the approval estimate. The current pricing map contains OpenRouter GPT-4o-mini/Haiku/Qwen entries but lacks an OpenRouter GPT-5.6-terra entry; using that model without explicit pricing would mark it unpriced and display zero estimated cost. The usage ledger's generic `api_calls` also includes local embeddings. Count paid calls from `usage.jsonl` with provider `openrouter` and `cached == false`.

## Scientific and execution risks to retain in the audit

- Dataset case IDs overlap; the pooled runner uses case IDs as dictionary keys. This must be resolved by a transparent internal namespace while retaining raw IDs and original data. See the separate dataset audit.
- Original Simple Memory uses content identity: `entry_id` hashes pool session and extracted fact text (`src/ams/memory/simple.py`, line 69). Identical facts can share IDs despite different source contexts. Every downloaded MPBench case has nonempty external context, so the main coarse MemLineage adapter labels all those parents as external; this content identity does not change its main gating decision on this workload. Retain original method behavior, save per-ingestion provenance separately, and treat entry-ownership diagnostics as potentially ambiguous. The supplemental LM-attribution variant could reuse a cached label across different source contexts and needs separate caution.
- The original judge falls back to lexical overlap for content filtering or unparsable answers. Inspect and report fallback counts rather than assuming every score is an LLM verdict. Empty answers receive a negative attack verdict; log them so generation failures cannot look like successful protection.
- The runner writes its CSV/summary at completion; a failed long run may have cache/usage data but no final table. Persist console logs and require complete row counts plus an explicit completion manifest before treating a run as finished.
- The cache prevents most repeated billing, but concurrent identical requests have no visible in-flight deduplication. Retries and model/provider changes can affect both paid calls and reproducibility. Preserve requested/resolved model IDs and finish reasons.
- `Config.load` does not interpolate environment variables. Environment-driven model selection belongs in a launcher that emits a resolved config; do not silently modify prompts or method parameters.
- `flag_rate_benign` is not automatically a detector false-positive rate: a benign query can retrieve genuinely poisoned records from another case in the shared pool. Likewise, `1-ASR` is not a detection true-positive rate. The available annotations primarily support ASR, retention recall, restraint, and their combined benign task accuracy. Classification FPR/FNR require defensible per-prediction labels and matching units.

Full-dataset paid execution remains pending explicit user approval. No new provenance defense, dynamic trust, defensive lesson mechanism, or training was added.
