# Deviation: early analysis of the GPT-4o-mini journal (owner-approved, 20 Nov 2026)

Protocol §9 says the analysis runs once with the frozen code, planned after P-B3 (GPT-4o-mini + Claude Haiku together).
On 20 Nov 2026 (~03:10 local) the owner chose "Analyse now": run the frozen analysis on the complete P-B2 journal
(`gpt_rerun3/`, 24/24 groups, 3,655,680 rows) before P-B3.

- Code, metrics, hypotheses, resamples and labels: unchanged (frozen rev7 code, `scripts/analyse_protocol_v2.py`).
- Output: `analysis_gpt_early/` (the final combined run after P-B3 goes to `analysis/`).
- The GPT-4o-mini numbers cannot change: the journal is complete and hash-checked. After P-B3 the final run adds
  Claude Haiku (Appendix A13) with the same pre-specified Table-7 baselines; nothing about P-B3 is chosen from these results.
- To be reported in the paper as: "an early look at the complete GPT-4o-mini results was taken before the Claude Haiku run (owner-approved)".
- The protocol text (§15) is hashed in the rev7 freeze that P-B3 needs, so the §15 entry is added after P-B3; until then this file is the record.
