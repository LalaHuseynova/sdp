# MEM-INV-Bench feasibility for S / SL (free, 23 Nov 2026)

**Question:** can our frozen methods be evaluated on MEM-INV-Bench (Louck, arXiv 2606.24322; repo `third_party/mem-inv-bench`, MIT licence, commit `050b2ea`), and is a paid run worth it?

**Cost:** $0. No LLM call and no network call; the local cached MiniLM was used. Third-party files were read as data (`ast` / `json`), never imported or executed. The frozen code is unchanged.

**Files:**
- `research_data/mem_inv_feasibility_20261123/sl_similarity.py` (script)
- `research_data/mem_inv_feasibility_20261123/sl_similarity.json` (every pair and its cosine)

## Why this check was needed

MEM-INV-Bench's defence, TMA-NM, is the closest published competitor:
- memory poisoning;
- provenance (write-time origin);
- "Sybil-resistant corroboration";
- a claimed 0% attack success at 100% utility.

Reviewers will ask why we neither use its benchmark nor compare with it. We needed a factual answer. It was also the cheapest check available, since the benchmark is already in the repo.

## 1. Structure: S, C and M cannot be tested on it (by construction)

Read from `v2/code/scenarios.py` and `v2/code/exp1_propensity.py::build_memory`:

| What S needs | MEM-INV-Bench v2 |
|---|---|
| Several items from one external source | **No.** Each scenario's memory holds 2–3 items: 1 poison item (or 2 for "corroborate") plus 1 trusted filler. |
| Unaudited sibling attacks from the same source | **No.** The 2 corroborating items come from *different* channels (`web` = public-web, `inbox` = public-mail), so different contributors *and* contexts. |
| Legitimate items from the attacker's own source (key stratum) | **No.** |
| Batches or sessions per source | **No** (one write per channel). |
| Retrieval ranking | **No.** The whole memory is shown to the agent. |
| Size | 8 attack scenarios × 4 laundering channels + 6 legitimate scenarios (v1: 12 + 26) |

**Consequence:** with an oracle audit on the poison, R already removes it, and S, C and M can add nothing. No audit evidence can reach an unaudited item from the same source, because there isn't one. This is the same structural gap as MPBench (only 3.1% propagation-reachable, no repeat contributor) and the reason the controlled workload exists.

Different problem, stated plainly: TMA-NM gates *consequential actions* by *channel origin* (static trust). S uses *audit evidence* to separate bad untrusted sources from good ones. MEM-INV-Bench has no repeated untrusted source, so the propagation question does not arise there.

## 2. What *can* be tested for free: SL's content lineage against their laundering

SL withholds a memory whose MiniLM cosine to an audited-unsafe memory is ≥ 0.8. The same model and threshold were applied to the benchmark texts directly.

| Test (audit A, check B) | Should SL block B? | Blocked | Cosine min / median / max |
|---|---|---:|---|
| v2 trusted-tool echo (L-b): poison → `[entity lookup] record on file: <value>` | yes | **0 / 8** | 0.45 / 0.58 / 0.79 |
| v2 manufactured corroboration (L-c): item A → item B | yes | **3 / 8** | 0.64 / 0.77 / 0.87 |
| v2 trusted filler vs poison / vs corroboration item | no | 0 / 8, 0 / 8 | ≤ 0.71 |
| v1-large attacker rewrite: static → adaptive | yes | **21 / 21** | 0.82 / 0.93 / 0.97 |
| v1-large static → white-box | yes | 19 / 21 | 0.73 / 0.92 / 0.96 |
| v1-large static → **benign twin** | no | **15 / 21 (false positive)** | 0.61 / 0.83 / 0.96 |
| head-to-head (4 published attack pipelines): static → adaptive / white-box | yes | 8 / 8, 7 / 8 | median 0.88 / 0.87 |
| head-to-head static → benign twin | no | 3 / 8 (false positive) | median 0.80 |
| v1 (small): static → adaptive / benign | yes / no | 3 / 9, 2 / 9 | median 0.77 / 0.70 |

**Reading:**
- **Paraphrase-style rewrites of an audited poison are mostly caught.** This contrasts with MEM-INV-Bench's finding that *edge-based* lineage (MemLineage-style) is malleable. Content lineage does not need the derivation edge.
- **Template launders are not caught.** The short tool echo and differently worded corroboration fall below τ = 0.8 most of the time.
- **False positives:** the benign twin shares its first sentence with the poisoned version, so whole-document similarity blocks it. In SAFE-Mem, SL compares *extracted claims*, so the numbers would differ. The mechanism is real, though: SL blocks every claim of an audited root, including benign claims of a poisoned document. This is a limitation to state.
- **Not tested:** the self-summarisation channel (L-a). Its paraphrases are LLM outputs. The v2 README says the transcripts are on Hugging Face, but the HF tree (checked 23 Nov) holds only parquet files and evidence zips, not `v2/transcripts/`.

## 3. Verdict

| Option | Decision |
|---|---|
| Paid answer-level run of S / C / M on MEM-INV-Bench | **Not worth it.** The outcome is known in advance (S = C = M = R once the poison is audited). |
| Use as a second dataset | **No.** Wrong structure for propagation. |
| Use in the paper | **Yes, at no cost:** (1) related work and positioning against TMA-NM; (2) one appendix paragraph or table: SL vs their laundering channels (above); (3) the SL false-positive limitation. |
| Second dataset | Stays **LoCoMo v1.2** (frozen; ~$6.25 to finish; owner approval pending). EnronQA is the optional third. |

**Caveats:**
- Raw texts were used, not SAFE-Mem claims.
- There are only 8–26 scenarios per set.
- This is a decision-level check, not answer-level.
- The benchmark is a single-author preprint whose v2 says it corrected its own v1.
