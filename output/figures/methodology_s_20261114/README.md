# Methodology figure: selective evidence propagation (S) on SAFE-Mem

| File | Use |
|---|---|
| `fig_method.pdf` | Vector PDF for Overleaf: 6.75 × 3.11 in, embedded Arial/Times subsets, no raster images |
| `fig_method.svg` | Editable source (real text; groups `panel-a`, `panel-b-S`, `panel-c-retrieval`, `legend`) |
| `fig_method.png` | Preview, 2780 × 1280 px |
| `make_figure.py` | Dependency-free generator; flags any text wider than its box or smaller than 16 units (≈ 5.6 pt) |

Regenerate: `python make_figure.py --out fig_method.svg`. The PDF and PNG were rendered from the SVG with headless Chrome (pass the output directory as an absolute path).

**Editing colours or text.**
- The SVG starts with a `PALETTE` comment listing each colour and its role. Every role uses its own hex value, so a find-and-replace of one hex recolours that role everywhere: in a text editor, Inkscape (Edit → Find/Replace) or Illustrator.
- The same constants sit at the top of `make_figure.py`.
- All labels are live `<text>` elements.
- Palette roles:
  - S (our contribution): soft lavender, `#7461B8` lines, `#4B3C8C` titles, `#ECE8F8` / `#F6F4FC` fills;
  - SAFE-Mem: neutral grey;
  - SL: muted teal;
  - S2-ID: restrained amber, dashed;
  - unsafe / withheld: red.
- Style: only panel (b) is framed; square-ish corners (radius 3); no icons; booktabs-style table rules. Line styles: solid = query path, dashed lavender = evidence, dotted teal = content near-copy (SL).
- A greyscale proof was checked: outcomes stay distinguishable by glyph and label, S2-ID by its dashed border, the near-copy path by its dotted line.

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{fig_method.pdf}
  \caption{...}  % see below
  \label{fig:method}
\end{figure*}
```

## Caption

**Selective evidence propagation on top of SAFE-Mem.** **(a)** Each external memory carries trusted provenance (contributor, context, batch). Five audit tickets, the same for R, C, M and S, record verdicts in an evidence ledger that counts at most one vote per origin. Four tickets flag the attacker's seeds as unsafe and one confirms a benign item of another contributor as safe. Under the optional boundary-verification protocol, the fifth ticket instead audits the attacker's other batch. An unrelated contributor U relays a near-copy of an unsafe-audited seed; U itself has no audit evidence. **(b)** S extends distrust from audited to unaudited memories only over scopes the evidence supports:
- batch: ≥ 1 unsafe origin in the batch;
- context: ≥ 2 across ≥ 2 batches;
- contributor: ≥ 4, with the context gate met in ≥ 2 contexts.

Each active scope is scored with risk (1+n_u)/(2+n_u+n_s), where n_u and n_s count distinct unsafe and safe audited origins. S takes the maximum penalty over active scopes, withholds at 0.25, and otherwise down-ranks. In the localized example only the batch scope is active, so S blocks the attacker's unaudited planted claim yet keeps the same contributor's useful note, which contextual (C) and multi-scope (M) reputation discard. **(c)** S acts inside SAFE-Mem's governed retrieval, after its unchanged admission filter. Provenance scopes cannot reach U's relay (S assigns it no penalty), so our optional extension SL vetoes, during candidate selection, any candidate whose embedding has cosine ≥ 0.8 to a claim of an unsafe-audited origin. A copy of an unaudited claim is not vetoed. The optional hybrid S2-ID adds MemLineage's sensitive-action gate: for a sensitive query whose final retrieved context contains any non-principal memory, it clears that context, so the answer model receives no memory for that query. S2-ID is evaluated under Sybil and laundering attacks because they move poison outside the audited scopes; the gate itself uses no identity signal and does not detect Sybils. User-owned and unknown-origin memories receive no source penalty, and answer judgments never update trust. Outcomes shown are an illustration of the mechanism, not experimental results; example content is fictional.

## Verification against the implementation (15 Nov 2026; method code unchanged by the protocol-v2 commits)

| Figure element | Code |
|---|---|
| Provenance (contributor, context, batch, attribution) | `Provenance`, `src/ams/research/dynamic/models.py:58` |
| One vote per origin; corrections and retractions | `EvidenceSnapshot.observations`, `ledger.py:274`; `_project`, `ledger.py:89` |
| Gates: batch ≥ 1; context ≥ 2 across ≥ 2 batches; contributor ≥ 4 with ≥ 2 qualifying contexts | `active_scopes`, `ledger.py:304-327` |
| risk = (1+n_u)/(2+n_u+n_s); pen = max(0, risk − ½) (n_u, n_s = distinct unsafe / safe origins; renamed from U, S to avoid a clash with the method name S) | `GroupStats`, `ledger.py:67-78` |
| S takes the max over supported scopes; C uses context; M uses max(batch, context, contributor) | `Policy.decide`, `policies.py:119-136` |
| Withhold at pen ≥ 0.25; otherwise score = cos − 0.5·pen | `policies.py:137-143` (weight 0.5, threshold 0.25) |
| Only authenticated external origins propagate; principal and unknown origins get no source penalty | `policies.py:119, 141`; `ledger.py:307` |
| Retrieval order: admission → direct findings → policy → re-rank and refill 4 + 4 → conflict check | `GovernedRetrieval.retrieve_with_trace`, `adapter.py:240-399` |
| Conflict check (step 5) runs on the already-served claims after refill and before the S2-ID gate; it only marks claims contested ("downgrade, never adjudicate") and removes none | `adapter.py:382-399`; `_resolve_conflicts`, `src/ams/memory/typed.py:828-877` |
| Localized example: only the batch scope is active (2 unsafe in batch 1). Context is not met (both flags in one batch); contributor is not met (no context has flags in 2 batches) | `active_scopes`, `ledger.py:313-326` |
| SL acts per candidate, before ranking: cos ≥ 0.8 to a claim of an unsafe-audited origin, principal exempt | `LineagePolicy.decide` and `blocked_records`, `lineage.py:54-102` |
| S2-ID acts on the final context: SENSITIVE query + any non-principal entry → empty context; S2-ID always includes SL | `_GatedReader`, `sv2.py:95-116`; `CANDIDATES` and `apply`, `sv2.py:47-150` |
| Audit allocation: 4 seed tickets (unsafe; 2 in each context) + 1 benign ticket of contributor B (safe), identical IDs for R, C, M, S | `oracle_audits`, `integration.py:308-343`; `AUDIT_TICKETS`, `design.py` |
| Boundary verification is an audit protocol: if a context's flags sit in one batch, the 5th ticket audits another batch of that contributor **instead of** the safe benign ticket (falls back to it when no context needs it) | `_followup_ticket`, `adaptive.py:333-358`; replacement in `overlay_and_tickets` (`last = _followup_ticket(...) or last`) |
| S2-ID clears the retrieved context (`entries=()`); the query itself is not refused | `_GatedReader.retrieve_with_trace`, `sv2.py:105-116` |
| Unlinked relay (contributor U): an unaudited copy of an audited seed, posted by an unrelated contributor, with its own root (only *linked* copies share the seed's root). In the workload the copied seed is A's context-Y seed s2a; the figure draws the copy of a context-X seed for compactness (lineage ignores context) | `design.py:20-28` (`U_BENIGN`, unlinked copy of s2a); `integration.py:153-158` (`copy_of` only for `linked_copy`); `adaptive.py:275-279` |
| S gives the relay no penalty: U has no audited origins, so no scope of U is active | `active_scopes`, `ledger.py:304-327` |
| SL reference set = claims of roots with an *unsafe* audit event, never S-withheld records; principal records exempt; a record verified safe for the use is not vetoed | `blocked_records`, `lineage.py:62-100`; `LineagePolicy.decide`, `lineage.py:54-59` |
| S2-ID is identity-blind (no Sybil detection); it is evaluated on the hard Sybil / own-batch / laundering cells (H4) | `sv2.py` docstring lines 16-25; protocol option B §6 (H4) |
| Localized example values: C 1/4 (2 unsafe in X); M 1/3 (4 unsafe in A); S batch 1/4 for batch 1 and no active scope for batch 2 | Worked from the formulas above with the localized placement in `design.py` (`PLACEMENT`) |

Not shown in the figure (by design): ACL checks (all-allow in the experiments), external evidence chunks (hidden by `external_evidence=false`), and any results.
