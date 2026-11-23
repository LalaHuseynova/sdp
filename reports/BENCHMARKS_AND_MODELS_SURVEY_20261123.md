# Second dataset and extra answer models: survey and recommendation (23 Nov 2026)

Free desk research for the ICML paper: arXiv abstracts and HTML, the public OpenRouter model list, and this repo's branches. Nothing was run and nothing was paid. Paper details come from abstracts and partial HTML reads, so check them before citing.

---

## 1. What S needs from a benchmark

S can only be tested where:
- (a) each memory item carries **provenance** (who sent it, in which channel, in which delivery or session);
- (b) one source sends **several items**, some poisoned and some legitimate, so the key stratum exists;
- (c) there are **utility labels** for the legitimate items.

Audits are added by us (oracle) on any benchmark. Most poisoning benchmarks fail (a) or (b): one payload per case and no sender identity. That is the same reason MPBench needed the controlled workload (only 102/3,241 attacks are propagation-reachable, and no contributor sends twice).

## 2. Memory-poisoning benchmarks and how well each fits

| Benchmark | What it is | Provenance labels? | Repeat source? | Code/data | Fit for S |
|---|---|---|---|---|---|
| **LoCoMo** (Maharana et al., ACL 2024) + our hijack | 10 long conversations, natural speakers and sessions, ~1,540 QA with evidence ids | **Yes, natural:** speaker = contributor, session = batch | Yes (hijacked speaker) | Public, CC BY-NC | **Good (already in progress, §3).** Gaps: one external speaker per conversation (no context or contributor gate); turn-level RAG, not SAFE-Mem; the attack template is ours. Others already use LoCoMo for poisoning (ER-MIA 2602.15344; the Nous provenance-capped defence 2606.22030) |
| **EnronQA** (Ryan et al., 2505.00263) | 103,638 real emails, 150 inboxes, 528,304 QA pairs | **Yes, natural and rich:** sender, recipients, thread, folder, date | Yes (many senders mail many times) | Public; licence not confirmed | **Best structural fit:** it is the only option with real many-sender, many-context provenance, so all three of S's gates can fire. New pipeline needed. Real people's emails raise an ethics note |
| **MEM-INV-Bench** (2606.24322; already in `third_party/mem-inv-bench`) | 12 domains, 5 consequential tools, laundering channels (self-summary, trusted-tool echo, **manufactured corroboration**), 8 models, Mem0 | **Yes:** write-time origin (trusted_tool / user / untrusted_external) | Partly (corroboration = several planted items) | GitHub + HF; licence not stated | **Must-cite competitor, possible head-to-head.** Its TMA-NM claims 0% attack at 100% utility with Sybil-resistant corroboration. It already compares MemLineage-style lineage and trust scoring |
| **LLMail-Inject** (2506.09956, SaTML 2025 challenge) | 208,095 real adaptive attack emails from 839 participants, against an email assistant | Sender = participant | Yes (many attempts per participant) | HF `microsoft/llmail-inject-challenge`, MIT (per card mirror) | **Interesting payload source** (real *adaptive* human attacks), but no benign siblings per sender and the target is a tool call, not memory. Stretch only |
| Utility Under Attack (2608.21230) | LongMemEval_S, 120 poisoned questions, 4 channel trust tiers | Channel tier only | 3 items per question | GitHub (aegis-memory) | Related work: shows that provenance *ranking* by channel tier is weak (p = 0.80) |
| LongMemEval (Wu et al., ICLR 2025) | ~50 user–assistant sessions per question | Sessions only; one human speaker | No natural second source | Public | Weak (no contributors) |
| MINJA (2503.03704) / MAFIA (2608.03844) / AMIA | Query-only memory injection; EHRAgent, RAP/WebShop, QA | No sender identity | MAFIA: 30–90 records per attacker | MINJA in `third_party/`; MAFIA code "will be released" | Poor: no provenance; MAFIA attacks *audited* agents (related work) |
| AgentPoison (NeurIPS 2024) | Trigger-optimized backdoor in memory/RAG; driving, QA, EHR | No | No | GitHub | Poor |
| ASB (ICLR 2025) | 10 agents, 400+ tools, a memory-poisoning attack class | No | No | GitHub | Poor |
| MemForm (2610.14431) | 1,016 cases, 5 formation interfaces | **Explicitly none** | ~3 forged records/case | GitHub | Poor |
| MemoryDojo (2611.09721) | 155 multi-session trajectories (AgentDojo domains incl. Slack), 5 memory systems | Partial (entry → source write) | No (future work) | Not released | Poor now |
| MemSecBench (2607.27080) | 310 write–execute–forget cases, 24 configs, includes a **Forget/repair** stage | Case-level carrier only | No | Not stated | Poor; related work on repair |
| MemPoison (Gao et al., 2607.14651, NeurIPS 2026) | 1,227 hand-validated cases, 3 memory architectures | Not confirmed | Multi-record composition | Public | Poor–unclear. **Name clash:** its benchmark is also called "MemPoison-Bench", like our MPBench (Dash et al., 2606.04329). Disambiguate in the paper |

## 3. LoCoMo status (co-author's work on branch `sdp/locomo-backup`, Windows machine)

The attached `PROTOCOL_LOCOMO_FULL_20261119.md` is an **old draft**. It was superseded by `reports/PROTOCOL_LOCOMO_V1.md` plus the v1.1 amendment (adds S2-ID) and the v1.2 amendment (infrastructure fixes).

- Feasibility (free) and pilot ($0.219) are done. The pilot showed S's regime map carries over to answers: 1-session hijack with A1 audits gives unaffected-session accuracy S .380 vs C/M .104 at equal ASR 0. A 2-session hijack makes S leak (.292 vs 0).
- The v1.1 paid run was **stopped by rule S2** (budget database failures under WSL) after 3 of 10 conversations. No outcome was inspected; the partial analysis is quarantined unread.
- v1.2 fixed the infrastructure and was re-frozen (digest `f04cc850…`). It is **waiting for the owner's approval**. The remaining 62,762 prompts are estimated at **~$6.25** (calibrated). Finished calls replay at $0.
- SAFE-Mem itself is not compared on LoCoMo (different substrate); that comparison stays on MPBench.

## 4. Recommendation

1. **Finish LoCoMo v1.2 as dataset 2.** It is the furthest along, cheapest (~$6 more), frozen, and already pre-registered, and LoCoMo poisoning has precedent in the literature. Present it as a *regime map* (where S wins, ties or leaks), as the protocol already says.
2. **MEM-INV-Bench: a free feasibility check now, cite in any case.** *(Done 23 Nov: S, C and M cannot be tested on it; SL can, at decision level. Not a second dataset. See `reports/MEM_INV_BENCH_FEASIBILITY_20261123.md`.)* It is already in the repo and has origin labels and laundering/corroboration attacks, so it speaks directly to the adaptive-attack weakness. Its TMA-NM is the closest competitor (origin-bound authority, Sybil-resistant corroboration), which raises the novelty bar. The paper must state the difference: TMA-NM uses static channel trust; S uses *audit evidence* to tell bad untrusted sources from good ones.
3. **EnronQA: the strongest optional third dataset**, only if there is time before the deadline. It is the only public data where contributor *and* context gates can fire on natural provenance, which answers the "synthetic contributors" criticism best. Cost: a new pipeline (about 1–2 weeks) plus paid answers. Check the licence and write an ethics note first.
4. **Cite but do not run:** MINJA, MAFIA, AgentPoison, ASB, MemForm, MemoryDojo, MemSecBench, MemPoison, Utility Under Attack, Nous. They lack the provenance structure S needs. Saying so in the paper is itself a point in favour of the controlled workload.

## 5. Extra answer models (OpenRouter public list, 23 Nov 2026; $ per 1M tokens in/out)

| Model | Price | Temperature? | Note |
|---|---|---|---|
| openai/gpt-4o-mini (current) | 0.15 / 0.60 | yes | main backbone and judge |
| anthropic/claude-haiku-5.5 (current) | 0.10 / 0.50 | **no** | why revisions 8–9 were needed |
| **google/gemini-3.1-flash-lite** (GA May 2026) | 0.25 / 1.50 | yes | **recommended Gemini**: current, stable id |
| google/gemini-2.5-flash-lite | 0.10 / 0.40 | yes | cheapest Gemini, but a July 2025 model with a likely deprecation risk |
| google/gemini-3.5-flash-lite | 0.30 / 2.50 | yes | newer, pricier output |
| **qwen/qwen3-235b-a22b-2507** (instruct) | 0.14 / 0.80 | yes | **recommended open-weight**: reproducible, answers the "provider drift" limitation |
| meta-llama/llama-3.3-70b-instruct | 0.71 / 0.71 | yes | open-weight alternative, pricier |

**Rough cost to add one model to the Option B Haiku design (8 cells × 11 methods).** This is scaled from Haiku's measured $1.19 for answers, assumes similar answer lengths, and adds ~$0.15 for the GPT-4o-mini judge:
- Gemini 3.1 Flash-Lite ≈ $3–4;
- Gemini 2.5 Flash-Lite ≈ $1.3;
- Qwen3-235B ≈ $2.

A dry run must replace these numbers.

**Cautions:**
- Gemini 3.x models may "think" by default, and thinking tokens are billed as output. Turn reasoning off and run a one-call canary first: the Haiku temperature 404 is the lesson.
- Adding a model is a code change (`APPROVED_MODELS` in `src/ams/llm/budget.py`) and a protocol amendment. It needs the owner's approval before any call.
- Retrieval decisions do not depend on the answer model. A third model only shows that the *answer-level* ranking is not model-specific. **Higher reviewer value:** run the LLM-based baselines (A-MemGuard, MemLineage classifier, sanitiser) with a stronger model, so no one can say they were weakened by GPT-4o-mini.
