# Result tables

Two independently labeled tables in the supplied academic style. Both PDFs contain selectable vector text and embedded Times New Roman fonts. PNGs are 600 dpi and are rendered directly from their corresponding PDFs.

| Table | PNG pixels | PDF page (points) |
|---|---:|---:|
| table_1_original_safemem_reproduction.pdf | 8800 x 2984 | 1056 x 358.0 |
| table_2_selective_propagation_pilot.pdf | 8800 x 3864 | 1056 x 463.6 |

## Scope and interpretation

- Table 1 compares the published GPT-4o-mini SAFE-Mem row with the complete local Original SAFE-Mem reproduction. It also shows the proposed method as unavailable on the full dataset; it is always the last row.
- LoCoMo 54.6% and its 1,540-question dataset size are paper references extracted from the local PDF, page 6. No local LoCoMo reproduction is claimed. The paper does not report the combined MPBench benign-utility value in Table 1.
- Table 2 includes all six methods with actual saved pilot outcomes: no-memory control, static SAFE-Mem, record-only R, contextual C, fixed multi-scope M and our selective method S. Paper baselines such as A-MemGuard and DRIFT were not evaluated on this pilot and their full-dataset scores are not substituted.
- Each pilot condition has 216 query events per method. The same 256 source cases are reused across the three overlays; they are not three independent datasets. Audit-reserved cases and probe cohorts can differ across conditions.
- Bold is computed from exact available values: minimize ASR, maximize Recall/Restraint/Utility/Accuracy, and include every tie. No-memory is included in this column-wise comparison; its zero ASR is an actual observed value, accompanied by zero retention. A single available value is bold by the same rule but is not evidence of comparative superiority.
- A dash means unavailable, never zero. Source-grounded QA is unvalidated and unscored. Utility is the original combined benign memory-use metric, not general task-answer accuracy.
- Human-verified safety labels and validated utility questions remain zero. Feedback was AI-simulated. The proposed method has NOT been evaluated on full MPBench; these pilot results do not establish an advantage.

## Provenance and reproduction

source_data.json records every displayed value, exact fraction, denominator, availability reason, bold flag, caption and source-file SHA-256. validation.json records the renderer checks; delivery_validation.json adds final raster, PDF and visual checks. No experiment output or result was modified.

Generator: scripts/render_research_result_tables.py. It refuses to overwrite an output directory and blocks networking. Rendering dependencies were installed in the separate temporary PDF-tool environment, without changing the frozen research .venv or uv.lock.

Re-render into a new directory:

```sh
tmp/pdfs/result_table_tools/bin/python scripts/render_research_result_tables.py --out output/pdf/my_new_tables --dpi 600
```

Tools: ReportLab 5.1.0; PyMuPDF 2.0. Font source files and hashes are in the validation record. The original research sources are listed in source_data.json relative to the repository root.

**New paid model/API cost: $0.** No training, defense evaluation, reviewer verdict or data selection was performed.
