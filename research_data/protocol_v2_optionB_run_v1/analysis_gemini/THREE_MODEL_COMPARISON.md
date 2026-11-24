# GPT-4o-mini vs Claude Haiku vs Gemini 3.1 Flash-Lite — consolidated comparison (24 Nov 2026)

**Gemini 3.1 Flash-Lite is a post-hoc additional backbone** (revision 10/11): it was added after the main analysis of 22 Nov and is **not pre-registered**. Its results are exploratory evidence of generalization, not confirmatory. All three use the same 8 attack cells, 11 methods, 24 groups, prompts, retrieval, contexts, judge (GPT-4o-mini) and metrics. Only the answering model changes. Data: reused MPBench v4 split, which makes this replication evidence, not fresh held-out data.

Sources (all in this folder): `analysis.json` (GPT-4o-mini), `backbone_analysis.json` (Claude Haiku), `extra_backbone_analysis.json` and appendix A14 (Gemini), and Table 7 in `tables.md`. The GPT-4o-mini and Claude Haiku numbers here are identical to the official `../analysis/` (checked: same JSON content; `tables.md`/`appendix.md` differ only by the added Gemini row and A14). Values are % (mean over 24 groups).

## 1. Run facts

| | GPT-4o-mini | Claude Haiku | Gemini 3.1 Flash-Lite |
|---|---|---|---|
| Status | pre-registered main | pre-registered second backbone | **post-hoc** third backbone |
| Answer settings | temp 0, 200 tokens | provider-default temperature (not set), reasoning off, 200 tokens | temp 0, reasoning off, 200 tokens |
| Journal rows | 46 cells (main run) | 212,520 (8 cells) | 212,520 (8 cells) |
| Paid answer calls | (P-B2) | 7,895 | 7,860 (+1 superseded 429 attempt) |
| Failed / empty answers | 0 / – | 0 / 6 | 0 / 0 |
| Answers cut at the 200-token limit | 1.5% | 1.2% | **11.2%** |
| Answer cost | – | $1.19 | $2.29 |
| Rows without an outcome | 0 | 0 | 0 |

## 2. Security — main result (localized attack, oracle audits)

| Method | target ASR ↓ GPT | Haiku | Gemini | judge ASR ↓ GPT | Haiku | Gemini |
|---|---|---|---|---|---|---|
| Original SAFE-Mem | 63 | 29 | 59 | 77 | 29 | 72 |
| A-MemGuard | 49 | 15 | 46 | 59 | 16 | 58 |
| MemLineage (best published) | 44 | 17 | 44 | 56 | 17 | 54 |
| LLM sanitiser | 56 | 25 | 51 | 69 | 25 | 64 |
| RandEC | 63 | 29 | 59 | 77 | 29 | 72 |
| C / M | 0 | 0 | 0 | 0 | 0 | 0 |
| **S / SL / S2-ID** | **0** | **0** | **0** | **0** | **0** | **0** |

## 3. Security — adaptive attacks (target ASR ↓, GPT / Haiku / Gemini)

| Attack | Original SAFE-Mem | MemLineage | C | S | SL | **S2-ID** |
|---|---|---|---|---|---|---|
| localized, distributed, harm-to-innocents (fp1) | 62 / 29 / 59 | 44 / 17 / 44 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | **0 / 0 / 0** |
| Sybil k=4 (own and shared) | 62 / 29 / 59 | 44 / 17 / 44 | 64 / 30 / 59 | 64 / 30 / 59 | 67 / 34 / 60 | **47 / 22 / 44** |
| Sybil k=4, random audits | 62 / 29 / 59 | 44 / 17 / 44 | 32 / 17 / 31 | 32 / 16 / 30 | 33 / 18 / 31 | **23 / 11 / 22** |
| Laundering r=4 | 62 / 29 / 59 | 44 / 17 / 44 | 66 / 33 / 64 | 66 / 32 / 64 | 66 / 34 / 60 | **46 / 22 / 44** |
| Laundering r=3, random audits | 62 / 29 / 59 | 44 / 17 / 44 | 31 / 15 / 27 | 30 / 14 / 28 | 29 / 14 / 28 | **20 / 9 / 20** |
| **Mean over the 8 cells** | 62.5 / 29.2 / 59.4 | 43.8 / 16.7 / 43.8 | 31.9 / 15.7 / 30.0 | 31.8 / 15.3 / 30.0 | 32.7 / 16.9 / 30.0 | **22.8 / 10.7 / 21.6** |
| **Worst cell** | 62 / 29 / 59 | 44 / 17 / 44 | 66 / 33 / 64 | 66 / 32 / 64 | 67 / 34 / 60 | **47 / 22 / 44** |

## 4. Utility (strict utility ↑, localized; GPT / Haiku / Gemini)

| Method | Strict utility | Harm to innocents (fp1): innocent strict utility |
|---|---|---|
| Original SAFE-Mem | 91 / 91 / 91 | 92 / 92 / 92 |
| A-MemGuard | 87 / 85 / 87 | 88 / 86 / 88 |
| MemLineage | 91 / 91 / 91 | 92 / 92 / 92 |
| C / M | 66 / 66 / 66 | 92 / 92(91 M) / 92 |
| **S** | **91 / 91 / 91** | 92 / 92 / 92 |
| SL / S2-ID | 91 / 91 / 91 | 86 / 86 / 86 |

Gemini's 11.2% cut answers did not lower its strict utility, which equals GPT-4o-mini's in every cell.

## 5. Pre-registered hypotheses (same rules applied; ✓/✗ descriptive, not confirmatory)

| Hypothesis | GPT-4o-mini | Claude Haiku | Gemini (post-hoc) |
|---|---|---|---|
| H1 vs C: S keeps more key utility at no ASR cost (+90) | ✓ | ✓ | ✓ |
| H1 vs M (+90) | ✓ | ✓ | ✓ |
| H2: S no worse than M on distributed attack | ✓ | ✓ | ✓ |
| H3: S beats the 4 published defences (S − MemLineage target ASR) | ✓ (−44) | ✓ (−17) | ✓ (−44) |
| H4: S2-ID lowers ASR vs S on Sybil/laundering | ✓ (−14) | ✓ (−7) | ✓ (−14) |
| H5: SL removes relay exposure (−58) | ✓ | ✓ | ✓ |
| H5 secondary: SL lowers relay target ASR | ✓ (−54) | ✗ (−12, bound 0) | ✓ (−50) |
| H6 vs C / vs M: S protects innocents better | ✗ / ✗ | ✗ / ✗ | ✗ / ✗ |

## 6. Generalization (Table 7)

| Backbone | S: target ASR / strict utility | Best published (MemLineage) | Best internal (C) | S − MemLineage, target ASR [95% CI] | S − C, strict utility [95% CI] |
|---|---|---|---|---|---|
| GPT-4o-mini | 0 / 91 | 44 / 91 | 0 / 66 | −44 [−54, −33] | +25 [+23, +27] |
| Claude Haiku | 0 / 91 | 17 / 91 | 0 / 66 | −17 [−22, −11] | +25 [+23, +27] |
| Gemini 3.1 Flash-Lite (post-hoc) | 0 / 91 | 44 / 91 | 0 / 66 | −44 [−54, −33] | +25 [+23, +27] |

## 7. What this means

1. **The defence generalizes to a third model family.** On Gemini, S/SL/S2-ID reach 0% attack success on the localized, distributed and harm-to-innocents cells with the same 91% utility, exactly as on GPT-4o-mini and Claude Haiku. The order of the methods is the same on all three models.
2. **Gemini behaves like GPT-4o-mini.** Without a defence it follows poisoned memories almost as often (59% vs 63%). Claude Haiku resists more on its own (29%), so on Haiku every method's ASR is about half as high.
3. **S2-ID is the best method under adaptive attacks on every model.** It cuts the worst-case ASR by about a third versus S (GPT 66→47, Haiku 32→22, Gemini 64→44). The adaptive Sybil/laundering attacks still succeed sometimes on all three models; this limitation does not depend on the model.
4. **The hypothesis outcomes on Gemini match GPT-4o-mini exactly** (H1–H5 ✓ including the H5 secondary; H6 ✗). Haiku differs only on the H5 secondary.
5. **Retrieval-level numbers (exposure) are the same for all three**, as expected: the same memory and retrieval are used; only the final answer changes.

## 8. Limitations specific to Gemini

- **Post-hoc and not pre-registered**: chosen after seeing the GPT and Haiku results; exploratory only.
- **11.2% of Gemini answers hit the 200-token limit** (GPT 1.5%, Haiku 1.2%). The limit was the same for every model by design. Strict utility was not affected, but the judge saw the shortened answers.
- Reused MPBench v4 split (replication evidence, not fresh held-out data), as for the other two models.
- The run hit the Google rate limit (HTTP 429) once before revision 11 and 5 times after it; every 429 after revision 11 was resent identically and answered on the first retry, so no answer is missing or duplicated.
