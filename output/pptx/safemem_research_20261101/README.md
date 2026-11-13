# SAFE-Mem research presentation

Open **SAFE_Mem_Research_Presentation.pptx** to present or edit the deck. It has 30 slides, 11 native tables, a native chart with embedded worksheet, editable diagram shapes/connectors, and detailed notes with sources on every slide. No slide content is flattened into a picture.

The three background slides cover one real MPBench example, our reproduction setup and the full-release reproduction comparison. Slides 5–28 focus on our own research (80% of the deck). The final two slides are technical appendices. The proposed method is last in each method comparison. Best performance includes all ties and the no-memory diagnostic control. Missing source-grounded QA and full-dataset S results are explicitly unavailable.

**SAFE_Mem_Research_Presentation.pdf** is a PowerPoint-rendered preview; **speaker_notes.md** is a separate readable copy of the notes. Full-slide previews are in `previews/`.

The deck reports preliminary AI-feedback development results, not a human-validated safety pilot. S did not improve ASR over C/M in this run. Original SAFE-Mem was reproduced on the full release; S has not been evaluated on the full release. Human safety/provenance and utility-question validation remains pending.

## Sources and checks

`source/verified_data.json` records the extracted numbers, actual D01 overlays and audit sequence, plus source hashes. `extract_data.py` reads existing repository material only; `build_deck.mjs` creates native PresentationML. The final file was exported through Microsoft PowerPoint 16.89.1 and independently reopened without a repair prompt. The bundled presentation runtime was unavailable on this host, so native PowerPoint export supplied the final editable file and PDF render.

`source/delivery_validation.json` records 229 passing checks, including displayed values against saved numerators/denominators, bold ties, native element counts, notes, source-file preservation, embedded chart data and PDF page count. Package and layout checks found no findings or warnings. Every slide was visually inspected at full size. Older draft exports are retained in `source/drafts/` and are not the deliverable.

No experiment was rerun, no research model/API call was made, and no original dataset, defense source or frozen experiment output was changed to produce this deck. Added research API cost: $0.
