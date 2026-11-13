# Image generation prompts

Method: built-in image generation. The final figure is a raster PNG. No benchmark or defense execution was performed to create it.

## Initial generation

Create ONE comprehensive but very clear scientific illustration of the WHOLE IMPLEMENTED RESEARCH PIPELINE for "Selective Evidence Propagation for Agent Memory". Intended for a machine-learning research paper. This must show the end-to-end implementation, not just one batch example and not the original SAFE-Mem architecture. Requested high-resolution canvas about 3000 x 2100, landscape 10:7 ratio. Crisp flat vector-like visual, white background, dark navy typography, teal for our additions, light gray for original components, amber/red for withheld records, muted lavender for private evaluation. Elegant thin outlines, restrained rounded corners, consistent icon system, excellent alignment and generous space. No gradients, shadows, 3D, photography, robot mascots, logos, ICML acceptance claims, performance charts, fake results, tiny dense paragraphs, or decorative clutter.

The figure should be understandable to a reader seeing the idea for the first time. Use exactly FOUR NUMBERED SECTIONS arranged in THREE HORIZONTAL BANDS. Top band section 1 spans full width. Middle band section 2 on left and section 3 on right. Bottom band section 4 spans full width. The content below is the complete text/layout specification; do not invent additional mechanisms. Allocate sufficient height to the middle policy panel. Total visible text around 250 words maximum. Each node uses a short heading and at most one or two short explanatory lines. Avoid long text inside arrows.

FIGURE TITLE at top:
"Selective evidence propagation: the complete implementation"

SECTION 1 — TOP FULL-WIDTH BAND
Heading: "1  Prepare memory and source relationships"
Four nodes left to right joined by arrows:
- "Original MPBench inputs" with document and email icons, small text "Email + File/Document", tiny note "Payloads unchanged".
- "Recover memory offline" with cache icon, small text "Saved claims + reconstructed chunks".
- "Add provenance metadata" with a small source-link tree icon, small text "Contributor · context · batch" and second small line "Record IDs · artifact IDs · source spans".
- "Freeze linked memory store" with database icon, small text "Claims + evidence chunks".
Below the provenance node, show a compact label "Synthetic assignments: Distributed / Localized / Uninformative". This is offline study construction, NOT a runtime detector input.
Below this band a tiny concise explanatory line:
"One contribution = one input; one batch = four independent contributions. Principal-authored records stay separate."
The memory store provides the initial memory for queries in section 4 via ONE clean connector down the OUTSIDE LEFT MARGIN, labelled "Shared memory". Do not route this through unrelated boxes. A source-link connection to section 2 may be a short downward connector labelled "Record + intended use".

SECTION 2 — MIDDLE LEFT PANEL, about 45% width
Heading: "2  Reveal review evidence"
A simple horizontal or vertical sequence:
- "Saved AI assessments" small text "Safe / unsafe / unresolved".
- arrow with label "Same 5 audit tickets".
- "Evidence ledger" drawn as an ordered log with three short sub-lines "Record + use + version", "One vote per incident", "Corrections rebuild state".
Below, a clean small banner:
"Pilot: all five audits arrive before scored questions"
This must visibly be saved AI feedback, NOT human truth, NOT a live detector reviewing every question. Tickets count contribution/use review opportunities, not extracted claims. Do not draw an answer-to-ledger feedback loop.
The evidence ledger sends ONE horizontal arrow to section 3 labelled "Current evidence".

SECTION 3 — MIDDLE RIGHT PANEL, about 55% width
Heading: "3  Compute how far risk spreads"
A compact four-row native-looking comparison table, no dense grid:
"R  Record-only"    "Exact reviewed record/use"
"C  Contextual"     "Contributor + context"
"M  Multi-scope"    "Maximum over all three scopes"
"S  Selective (ours)" "Maximum over supported scopes"
Our S row last, teal highlight, others neutral.
Below this comparison, a clear THREE-STEP MINI LADDER labelled "S support rules":
"Batch: ≥1 unsafe incident"
"Context: ≥2, across two batches"
"Contributor: ≥4, across two contexts*"
Under the ladder in smaller but legible text:
"*At least two unsafe incidents spanning both batches in each context."
Then one compact formula line:
"d = max(0, (1 + U) / (2 + U + Safe) − 0.5)"
Use clear typography, not malformed math. Under it a short note:
"Only direct audits count; unreviewed records get no safety label."
U and Safe refer to distinct incident counts; no need further dense text in figure.
This policy module sends ONE downward arrow labelled "Current findings + chosen policy" to the combined findings/penalty box in section 4.
Do not imply scope support alone hard-blocks everything. One unsafe finding gives d ≈ 0.167, below the hard gate. Do not include random equations or probabilities.

SECTION 4 — BOTTOM FULL-WIDTH BAND
Heading: "4  Filter retrieval, answer, and evaluate"
A clean left-to-right flow with SIX short nodes, ample room:
1. "Question + candidates" small text "Claims and chunks".
2. "Original authority + permissions".
3. "Direct findings + policy penalty" small text "Exact safe-use exception".
4. "Rank eligible records + refill" small text "score = cosine − 0.5d".
5. "Original answer model".
6. "Private evaluation" small text "ASR · retention · restraint".
The private evaluation node must be visibly separated by a dashed vertical boundary and lavender outline. Its arrow receives saved ANSWERS ONLY from the answer model. NO return arrows to evidence, memory, or trust.
The section 3 state arrow must enter node 3 from above, unambiguously. No other lines can run through it or the node text.
From nodes 2 and 3, clean red/orange reject arrows join a small TERMINAL node BELOW them:
"Withhold from answer context"
Label the two branches concisely:
from authority: "Denied"
from findings: "Unsafe use or d ≥ 0.25"
The terminal withhold node has NO outgoing connection. Ineligible records do not reach refill or model. Exact safe-use findings skip reputation penalties but never override authority or permissions.
Below the normal query path, a single unobtrusive footer bar:
"Sequential execution · saved responses · checkpoints / restart · shared spending guard"
This is execution infrastructure, not a new model or new safety gate.

FINAL SMALL FOOTNOTE at the bottom, readable and distinct from content:
"Implemented prototype; preliminary subset evaluation only. AI review labels await human validation."
Second short footnote:
"Private labels, hidden profiles and future audits stay outside defense inputs."

VISUAL QUALITY
Clear visual hierarchy, consistent icon sizes, minimal words, good whitespace. Mark reused/original nodes pale gray, our added metadata/ledger/policy/retrieval nodes pale teal; evaluation muted lavender. Section numbering 1-4 must make reading order obvious. Avoid crossing arrows, double-headed arrows, extra feedback loops, or ambiguous arrows touching rejection branches. This is a faithful implementation schematic, not a claim that efficacy is demonstrated or that our method has run on the full dataset.

## First connector correction

Correct three connections in this complete implementation figure. Preserve the four sections, all words, all nodes and icons, formulas, counts, colors, and main left-to-right paths. The current overall design is good.

1. FIX THE MEMORY SOURCE. The existing left "Shared memory" line incorrectly starts at the Original MPBench inputs. Remove the short segment touching Original MPBench inputs. Reconnect the existing left vertical Shared memory line to the OUTPUT of "Freeze linked memory store", not to raw inputs, not to recovery, not to metadata. Route a thin teal elbow connector from the TOP edge of the frozen store box upward into the clear horizontal gap immediately ABOVE the four preparation nodes and BELOW the section 1 heading, then leftwards through that gap to the existing outer-left Shared memory rail. The top horizontal segment must not cross any node or heading text. The rail still enters the Question + candidates node from its left. Put a directional arrow at Question + candidates. This makes it unambiguous that query candidates come from the FROZEN MEMORY STORE.

2. REMOVE the downward arrow and label "Record + intended use" that currently points from metadata into section 3's heading. It is a misleading connection. Leave this small inter-panel area blank. Saved AI assessments already contain their reviewed record/use; no new connector is needed there.

3. FIX THE POLICY OUTPUT. The downward "Current findings + chosen policy" arrow must enter the TOP EDGE of the "Direct findings + policy penalty" node in section 4, rather than stopping at the section 4 panel border above the answer model. Route from the bottom of section 3 down through the open space on the RIGHT of the section 4 heading, then turn LEFT in the whitespace BELOW that heading and ABOVE the row of query nodes, then turn DOWN into the top center of the Direct findings + policy penalty node. Keep this connector completely above the normal query row until its final short downward arrow. No line can cross heading text, other node text, the Private evaluation boundary, or rejection arrows. If needed, move the row of six query nodes and the rejection box slightly downward to create a clean corridor, preserving spacing and keeping all text fully inside the figure.

Do not alter the policies, support rules, score, rejection paths, or private evaluation boundary. Keep both rejection arrows into the terminal Withhold node, with no outgoing arrow. Keep private evaluation receiving Answers only with no feedback arrow. Keep the same canvas and ensure nothing is cropped.

## Final memory-connection correction

Make ONE repair only: the teal "Shared memory" connection is broken in this figure. Preserve ALL text, all boxes, all other arrows, all colors and the complete layout.

ERASE the stray teal line running beside the section 1 heading toward the frozen store. It currently starts immediately after the words "source relationships" and runs rightwards. Remove this entire top horizontal line and its little right-hand vertical segment.

Replace it with a SINGLE UNBROKEN teal connector from the RIGHT EDGE of the "Freeze linked memory store" box to the existing far-left Shared memory rail. Use the following exact geometric route, referring to the attached image's approximately 1500 x 1050 pixel canvas:
- Start at the midpoint of the frozen store box's RIGHT EDGE (around x1460, y170).
- Go RIGHT to the narrow empty margin at x1488.
- Go DOWN to y321, which is the empty horizontal strip just BELOW the gray explanatory bar and just ABOVE the bottom border of section 1.
- Go LEFT across that empty strip at y321 all the way to x50. This horizontal line must NOT touch the explanatory text or the section headings.
- At x50, join the existing vertical Shared memory rail, which continues DOWN and enters the Question + candidates box from the left.
Keep the existing arrowhead where the rail enters Question + candidates. No gap anywhere along this source-to-query wire. This wire should not originate at raw inputs or metadata. It carries frozen memory only.
Do not draw any line across the title or section 1 heading. Do not change the already-correct current-findings arrow entering the Direct findings + policy penalty node. Do not change any other content.

