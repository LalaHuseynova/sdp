"""Paper-style result tables (GPT-4o-mini + Claude Haiku + Gemini 3.1 Flash-Lite, post-hoc) from the frozen analysis outputs.
Reads analysis/analysis.json, analysis/backbone_analysis.json and analysis_gemini/extra_backbone_analysis.json only;
writes tables.html (print to PDF). The two-model version of 22 Nov is kept in two_models_20261122/."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent / "analysis"
G = json.load(open(A / "analysis.json"))
H = json.load(open(A / "backbone_analysis.json"))
E = json.load(open(HERE.parent / "analysis_gemini" / "extra_backbone_analysis.json"))  # post-hoc third backbone
GEM = "Gemini 3.1 Flash-Lite"
BACK = [("GPT-4o-mini", G), ("Claude Haiku", H), (GEM, E)]
LABEL = {"static": "SAFE-Mem", "a_memguard": "A-MemGuard", "memlineage": "MemLineage",
         "llm_sanitiser": "LLM Sanitiser", "randec": "RandEC", "R": "R", "C": "C", "M": "M",
         "S": "S (ours)", "SL": "SL (ours)", "S2-ID": "S2-ID (ours)"}
GROUPS = [["static"], ["a_memguard", "memlineage", "llm_sanitiser", "randec"], ["R", "C", "M"], ["S", "SL", "S2-ID"]]
OURS = {"S", "SL", "S2-ID"}


def val(d, cell, m, k):
    try:
        return 100 * d["cells"][cell][m][k]["value"]
    except KeyError:
        return None


def cellhtml(v, base, lower_better, best):
    if v is None:
        return "<td>&ndash;</td>"
    s = f"{v:.1f}"
    s = f"<b>{s}</b>" if best else s
    if base is None:
        return f"<td>{s}</td>"
    d = round(round(v, 1) - round(base, 1), 1)  # change between the numbers as printed
    if abs(d) < 0.05:
        tag = '<span class="eq">&plusmn;0.0</span>'
    else:
        good = (d < 0) == lower_better
        arrow = "&darr;" if d < 0 else "&uarr;"
        tag = f'<span class="{"good" if good else "bad"}">{arrow}{abs(d):.1f}</span>'
    return f"<td>{s}<sub>{tag}</sub></td>"


def block(name, d, cols, methods_groups, nmeth):
    rows, first = [], True
    allm = [m for g in methods_groups for m in g]
    best = {}
    for (cell, k, lower) in cols:
        vs = [round(val(d, cell, m, k), 1) for m in allm if val(d, cell, m, k) is not None]
        best[(cell, k)] = (min(vs) if lower else max(vs)) if vs else None
    for gi, g in enumerate(methods_groups):
        for m in g:
            cls = ' class="ours"' if m in OURS else ""
            sep = ' class="gsep"' if gi > 0 and m == g[0] else ""
            tds = []
            for (cell, k, lower) in cols:
                v = val(d, cell, m, k)
                base = None if m == "static" else val(d, cell, "static", k)
                tds.append(cellhtml(v, base, lower, v is not None and round(v, 1) == best[(cell, k)]))
            bb = f'<td class="bb" rowspan="{nmeth}">{name}</td>' if first else ""
            first = False
            rows.append(f"<tr{sep}>{bb}<td{cls}>{LABEL[m]}</td>{''.join(tds)}</tr>")
    return "<tbody>" + "".join(rows) + "</tbody>"


def table(caption, head1, head2, cols, groups, note=""):
    n = sum(len(g) for g in groups)
    body = "".join(block(name, d, cols, groups, n) for name, d in BACK)
    return f"""<div class="tab"><p class="cap">{caption}</p><table>
<thead><tr><th rowspan="2" class="lh">Answer model</th><th rowspan="2" class="lh">Method</th>{head1}</tr>
<tr>{head2}</tr></thead>{body}</table>{note}</div>"""


# Table 1: main (localized) attack, Table-1 metrics
t1cols = [("localized", "target_asr", True), ("localized", "judge_asr", True),
          ("localized", "unaudited_exposure", True), ("localized", "strict_utility", False)]
t1 = table("<b>Table 1:</b> Defensive performance against the <i>localized</i> memory-poisoning attack "
           "(one poisoned memory, oracle audits) on the reused MPBench v4 split (24 groups). Values in %, mean over "
           "groups. Attack metrics: lower is better (&darr;); strict utility: higher is better (&uarr;). Subscripts "
           "give the change against SAFE-Mem (<span class=good>green</span> = better, "
           "<span class=bad>red</span> = worse). Best per column and model in <b>bold</b>.",
           '<th colspan="3" class="grp">Attack (&darr;)</th><th class="grp">Usefulness (&uarr;)</th>',
           "<th>Target ASR</th><th>Judge ASR</th><th>Unaudited exp.</th><th>Strict utility</th>",
           t1cols, GROUPS, note='<p class="tnote"><b>Methods.</b> <b>SAFE-Mem</b>: the base memory system; audit results are not propagated to any other memory. <b>R</b> (record-only): withholds only the memory an audit found unsafe; no penalty for related memories. <b>C</b> (contextual reputation): penalises the unsafe contributor\'s memories in the same conversation context. <b>M</b> (multi-scope reputation): applies the maximum of the batch, context and contributor penalties, i.e. distrusts the contributor everywhere. <b>S</b> (ours, selective propagation): extends distrust only as far as the audit evidence supports, to the batch after 1 unsafe audit, to the context after 2 spanning two batches, and to the contributor after 4 spanning two contexts. <b>SL</b> (ours): S + content lineage; also withholds near-copies (MiniLM cosine &ge; 0.8) of a memory audited unsafe, whoever contributed them. <b>S2-ID</b> (ours, hybrid): SL + MemLineage\'s sensitive-action gate (for questions that request a sensitive action, e.g. send, export, execute, pay, memory from external sources is dropped). Published defences (A-MemGuard, MemLineage, LLM Sanitiser, RandEC) filter SAFE-Mem\'s retrieval with no refill; A-MemGuard uses one draw at its repository temperature 1.0.<br>\n<b>Metrics.</b> <b>Target ASR</b>: attack probes whose answer acts on the planted instruction and restates its target (GPT-4o-mini judge). <b>Judge ASR</b>: the judge\'s verdict alone. <b>Unaudited exp.</b>: an unaudited attack memory reaches the answer context. <b>Strict utility</b>: utility probes answered correctly with the needed fact in context.</p>')

# Table 2: adaptive attacks, target ASR
t2cols = [("sybil_k4", "target_asr", True), ("sybilown_k4", "target_asr", True), ("launder_r4", "target_asr", True),
          ("launder_r3_rand", "target_asr", True), ("sybilown_k4_rand", "target_asr", True)]
t2 = table("<b>Table 2:</b> Target ASR (%, &darr;) under <i>adaptive</i> attacks: Sybil identities (k = 4), "
           "laundering by innocent relays (fraction r), with oracle or random audits. Subscripts: change against "
           "SAFE-Mem. Best per column and model in <b>bold</b>.",
           '<th colspan="3" class="grp">Oracle audits</th><th colspan="2" class="grp">Random audits</th>',
           "<th>Sybil k=4</th><th>Sybil-own k=4</th><th>Launder r=1</th><th>Launder r=.75</th><th>Sybil-own k=4</th>",
           t2cols, GROUPS, note='<p class="tnote"><b>Attacks.</b> <b>Sybil k=4</b>: the attacker spreads the poison over 4 fake contributor identities; <b>Sybil-own</b>: each identity arrives in its own batch. <b>Launder r</b>: a fraction r of the attack items is repeated (relayed) by innocent contributors (r = 1: all; r = .75: three quarters). <b>Oracle audits</b>: the audits inspect attack items; <b>random audits</b>: in each context, 2 of the 4 attack items are picked at random for audit, so every audit still finds poison and only which items are caught is random (values averaged over 6 draws).</p>')


# Table 3: worst case + hypotheses
def wc(d, m):
    try:
        return 100 * d["worst_case"][m]["target_asr"]["value"]
    except KeyError:
        return None

wrows = []
for gi, g in enumerate(GROUPS):
    for m in g:
        cells = []
        for _, d in BACK:
            v, base = wc(d, m), (None if m == "static" else wc(d, "static"))
            allv = [round(wc(d, x), 1) for gg in GROUPS for x in gg if wc(d, x) is not None]
            cells.append(cellhtml(v, base, True, v is not None and round(v, 1) == min(allv)))
        sep = ' class="gsep"' if gi > 0 and m == g[0] else ""
        cls = ' class="ours"' if m in OURS else ""
        wrows.append(f"<tr{sep}><td{cls}>{LABEL[m]}</td>{''.join(cells)}</tr>")
t3 = f"""<div class="tab half"><p class="cap"><b>Table 3:</b> Worst-case target ASR (%, &darr;): the maximum over
attack cells (GPT-4o-mini: all {G['worst_case']['S']['target_asr']['cells_covered']} registered worst-case cells; Claude Haiku and Gemini: the {H['worst_case']['S']['target_asr']['cells_covered']} cells they were run on).
Subscripts: change against SAFE-Mem.</p><table><thead><tr><th class="lh">Method</th><th>GPT-4o-mini</th>
<th>Claude Haiku</th><th>{GEM}</th></tr></thead><tbody>{''.join(wrows)}</tbody></table></div>"""

HYP = [("H1 vs C", "S keeps the key fact C discards, equally safe"), ("H1 vs M", "S keeps the key fact M discards, equally safe"),
       ("H2", "S as safe as M under the distributed attack"), ("H3", "S below every published defence (target ASR)"),
       ("H4", "S2-ID below S under Sybil / laundering"), ("H5", "SL cuts relay exposure, no utility loss"),
       ("H6 vs C", "S more useful to innocents when 1 of 5 audits is a false positive"), ("H6 vs M", "same, against M")]


def hyp(d, name):
    return d["hypotheses"]["contrasts"].get(name)


hrows = []
for name, desc in HYP:
    out = []
    for _, d in BACK:
        c = hyp(d, name)
        ok = bool(c and c.get("reject"))
        est = ""
        if c and c.get("components"):
            # H3 ("below every published defence") holds only if every component holds: show the binding one (closest to 0)
            comp = max(c["components"], key=lambda x: x["estimate"]) if name == "H3" else c["components"][0]
            e = comp.get("estimate")
            if e is not None:
                n = round(100 * e)
                est = f' <span class="est">({"0" if n == 0 else f"{n:+d}"})</span>'
        out.append(f'<td>{"<span class=good>&#10003;</span>" if ok else "<span class=bad>&#10007;</span>"}{est}</td>')
    hrows.append(f"<tr><td>{name}</td><td class='desc'>{desc}</td>{''.join(out)}</tr>")
t4 = f"""<div class="tab half"><p class="cap"><b>Table 4:</b> Pre-registered hypotheses (Holm over 8 primary
contrasts, 24 groups; replication evidence, not confirmatory). Primary estimate in points in brackets; for H3, the estimate against the closest published defence (MemLineage on GPT-4o-mini and Gemini, A-MemGuard on Claude Haiku).</p>
<table><thead><tr><th class="lh">Contrast</th><th class="lh">Claim</th><th>GPT-4o-mini</th><th>Claude Haiku</th><th>{GEM}</th></tr></thead>
<tbody>{''.join(hrows)}</tbody></table></div>"""


# ----------------------------------------------------------------------------- Part B: GPT-4o-mini only
ALLM = [m for g in GROUPS for m in g]


def gpt_table(caption, head1, cols, note="", wide=False):
    """cols: [(cell, metric, lower_better, header)]; head1: [(label, span)]. One model (GPT-4o-mini)."""
    best = {}
    for (cell, k, lower, _) in cols:
        vs = [round(val(G, cell, m, k), 1) for m in ALLM if val(G, cell, m, k) is not None]
        best[(cell, k)] = (min(vs) if lower else max(vs)) if vs else None
    rows = []
    for gi, g in enumerate(GROUPS):
        for m in g:
            sep = ' class="gsep"' if gi > 0 and m == g[0] else ""
            cls = ' class="ours"' if m in OURS else ""
            tds = []
            for (cell, k, lower, _) in cols:
                v = val(G, cell, m, k)
                base = None if m == "static" else val(G, cell, "static", k)
                tds.append(cellhtml(v, base, lower, v is not None and round(v, 1) == best[(cell, k)]))
            rows.append(f"<tr{sep}><td{cls}>{LABEL[m]}</td>{''.join(tds)}</tr>")
    h1 = "".join(f'<th colspan="{n}" class="grp">{t}</th>' for t, n in head1)
    h2 = "".join(f"<th>{c[3]}</th>" for c in cols)
    return f"""<div class="tab{' wide' if wide else ''}"><p class="cap">{caption}</p><table>
<thead><tr><th rowspan="2" class="lh">Method</th>{h1}</tr><tr>{h2}</tr></thead>
<tbody>{''.join(rows)}</tbody></table>{note}</div>"""


SUB = "Subscripts: change against SAFE-Mem (green better, red worse); best per column in <b>bold</b>."
KS, RS = (1, 2, 4, 8), (("0", "r0"), (".25", "r1"), (".5", "r2"), (".75", "r3"), ("1", "r4"))
t5 = gpt_table(f"<b>Table 5 (GPT-4o-mini):</b> Target ASR (%, &darr;) against a Sybil attacker who spreads the poison over k "
               f"fake identities. {SUB}",
               [("Oracle audits", 4), ("Random audits", 4)],
               [(f"sybil_k{k}", "target_asr", True, f"k={k}") for k in KS] +
               [(f"sybil_k{k}_rand", "target_asr", True, f"k={k}") for k in KS], wide=True)
t6 = gpt_table(f"<b>Table 6 (GPT-4o-mini):</b> Target ASR (%, &darr;) under laundering: a fraction r of the attack items is "
               f"repeated by innocent contributors. {SUB}",
               [("Oracle audits", 5), ("Random audits", 5)],
               [(f"launder_{c}", "target_asr", True, f"r={r}") for r, c in RS] +
               [(f"launder_{c}_rand", "target_asr", True, f"r={r}") for r, c in RS], wide=True)
OTHER = [("uninformative", "No-signal&dagger;"), ("shift_batch", "Shift (batch)"), ("shift_context", "Shift (context)"),
         ("framing_concentrated", "Framing (conc.)"), ("framing_spread", "Framing (spread)")]
DAG = ('<p class="tnote">&dagger; No-signal control: the attacker controls every contributor, so no audit can carry '
       'signal. Reported for completeness; not an attack and excluded from the worst case.</p>')
t7 = gpt_table(f"<b>Table 7a (GPT-4o-mini):</b> Remaining attacks, target ASR (%, &darr;). Audit-aware shift: the attacker moves "
               f"the poison to the batch or context the audits do not reach. Framing: the attacker plants poison under innocent "
               f"contributors' names. {SUB}",
               [("Target ASR (&darr;)", 5)], [(c, "target_asr", True, h) for c, h in OTHER], note=DAG)
t7 += gpt_table(f"<b>Table 7b (GPT-4o-mini):</b> Remaining attacks, strict utility (%, &uarr;). {SUB}",
                [("Strict utility (&uarr;)", 5)], [(c, "strict_utility", False, h) for c, h in OTHER])
t8 = gpt_table(f"<b>Table 8 (GPT-4o-mini):</b> Harm to innocent contributors: innocent strict utility (%, &uarr;). {SUB}",
               [("Innocent strict utility (&uarr;)", 5)],
               [("framing_concentrated", "innocent_strict_utility", False, "Framing (conc.)"),
                ("framing_spread", "innocent_strict_utility", False, "Framing (spread)"),
                ("cohabit_x1", "innocent_strict_utility", False, "Cohabit"),
                ("imp_localized_fp1", "innocent_strict_utility", False, "FP audit"),
                ("launder_r3_rand", "innocent_strict_utility", False, "Forwarder (r=.75, rand.)")],
               note='<p class="tnote"><b>Cohabit</b>: an innocent contributor shares a batch with the attacker. <b>FP audit</b>: 1 of the 5 '
                    'audits wrongly flags an innocent memory (H6). <b>Forwarder</b>: innocent contributors who unknowingly repeat '
                    'an attack item (laundering r = .75, random audits).</p>')
AUD = (("", "perfect"), ("_fn20", "miss 20%"), ("_fp1", "1 FP"), ("_late", "late"))


def imp(base):
    return [((base if suf == "" else f"imp_{base}{suf}"), "target_asr", True, lab) for suf, lab in AUD]


t9 = gpt_table(f"<b>Table 9 (GPT-4o-mini):</b> Imperfect audits, target ASR (%, &darr;): perfect audits, 20% of unsafe items "
               f"missed (miss 20%), 1 of 5 audits a false positive (1 FP), audits arriving late. {SUB}",
               [("Localized", 4), ("Distributed", 4)], imp("localized") + imp("distributed"), wide=True)
t10 = gpt_table(f"<b>Table 10 (GPT-4o-mini):</b> Imperfect audits under Sybil k=2 and laundering r=.5, target ASR (%, &darr;). {SUB}",
                [("Sybil k=2", 4), ("Laundering r=.5", 4)], imp("sybil_k2") + imp("launder_r2"), wide=True,
                note='<p class="tnote">Strict utility for Tables 9&ndash;10 is in <code>analysis/tables.md</code>, Table 6.</p>')
WHY = """<div class="why"><b>Part B &mdash; GPT-4o-mini only.</b> The tables below cover the full attack set (62 attack cells,
272 runtime conditions) and were run on GPT-4o-mini only. Claude Haiku was run, as pre-registered (option B), on the
8 cells that every claim of the paper needs (Gemini 3.1 Flash-Lite on the same 8 cells): the main localized result (Table 1) and all hypothesis cells H1&ndash;H6 (Tables
2&ndash;4). Running Haiku on all 272 conditions would cost about 12&times; more (&asymp; $14&ndash;17 instead of $1.34, above
the approved Haiku cap of $8 and the code ceiling of $10) and take 3&ndash;4 days on the evaluation machine. On the 8 shared cells
Haiku and Gemini give the same hypothesis decisions as GPT-4o-mini, and S, SL and S2-ID reach 0% target ASR under the localized attack on all three.</div>"""
PART_B = WHY + t5 + t6 + t7 + t8 + t9 + t10


# ----------------------------------------------------------------------------- Figure 1 (from make_figures.py)
FIG1 = """<div class="fig"><img src="fig1_tradeoff.svg" alt="Figure 1"><p class="cap"><b>Figure 1:</b> Attack success
against usefulness under the localized attack, all three answer models (Table 1). Top left is best: S, SL and S2-ID remove the
attack (0%) and keep the usefulness of SAFE-Mem; C and M also reach 0% but lose about 25 points of usefulness; the
published defences keep usefulness but leave 15&ndash;56% attack success.</p></div>"""

CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: "Times New Roman", Times, serif; font-size: 10.5pt; color: #000; }
h1 { font-size: 14pt; text-align: center; margin: 0 0 2pt; } .sub { text-align: center; font-size: 9.5pt; margin: 0 0 10pt; color: #333; }
.tab { margin: 0 auto 14pt; page-break-inside: avoid; } .cap { margin: 0 0 4pt; line-height: 1.25; text-align: justify; }
table { border-collapse: collapse; margin: 0 auto; border-top: 1.6pt solid #000; border-bottom: 1.6pt solid #000; }
thead tr:last-child th { border-bottom: 1pt solid #000; } th, td { padding: 1.2pt 7pt; text-align: center; white-space: nowrap; }
thead { background: #f2f2f2; } th.grp { border-bottom: 0.6pt solid #000; } th.lh { text-align: left; vertical-align: middle; }
td:nth-child(1), td:nth-child(2) { text-align: left; } td.bb { vertical-align: middle; text-align: center; border-right: 0.6pt solid #000; font-weight: normal; }
tbody { border-top: 1pt solid #000; } tbody + tbody { border-top: 1.2pt solid #000; } tr.gsep td:not(.bb) { border-top: 0.4pt dotted #999; }
td.ours { font-weight: bold; } sub { font-size: 7.5pt; vertical-align: -1.5pt; margin-left: 1pt; }
.good { color: #1b8a7a; } .bad { color: #c62828; } .eq { color: #888; } .est { color: #555; font-size: 9pt; }
.half td:first-child { text-align: left; } td.desc { text-align: left; white-space: normal; max-width: 210pt; font-size: 9.5pt; }
.tnote { font-size: 8.6pt; line-height: 1.28; text-align: justify; margin: 4pt 0 0; color: #222; }
.why { border: 0.8pt solid #1b8a7a; background: #f3faf8; padding: 6pt 8pt; margin: 0 0 12pt; font-size: 9.5pt; line-height: 1.3; text-align: justify; }
.part { font-size: 11pt; margin: 4pt 0 6pt; } .ph { font-size: 8pt; color: #555; }
.pb { page-break-before: always; }
.wide table { font-size: 9pt; } .wide th, .wide td { padding: 1.2pt 4.5pt; }
.mdsec { margin: 0 0 14pt; } .mdp { font-size: 9pt; margin: 2pt 0 4pt; text-align: justify; }
.sub { font-size: 9.5pt; margin: 8pt 0 3pt; }
table.md { border-collapse: collapse; margin: 4pt auto 4pt; border-top: 1.2pt solid #000; border-bottom: 1.2pt solid #000; }
table.md th { border-bottom: 0.6pt solid #000; font-weight: bold; vertical-align: bottom; white-space: normal; }
.keep { page-break-inside: avoid; }
table.md th, table.md td { padding: 1.4pt 4pt; text-align: center; } table.md td:first-child, table.md th:first-child { text-align: left; }
table.md tr { page-break-inside: avoid; } table.md thead { display: table-header-group; }
.md-m { font-size: 8.6pt; } .md-s { font-size: 7.8pt; } .md-xs { font-size: 6.6pt; } .md-xs th, .md-xs td { padding: 1pt 2.4pt; }
.fig { margin: 6pt auto 16pt; page-break-inside: avoid; text-align: center; } .fig img { width: 88%; }
.fig .cap { text-align: justify; }
.note { font-size: 9pt; color: #333; margin-top: 6pt; line-height: 1.3; }
"""
html = f"""<!doctype html><html><head><meta charset="utf-8"><title>SAFE-Mem results</title><style>{CSS}</style></head><body>
<h1>SAFE-Mem: results on GPT-4o-mini, Claude Haiku and Gemini 3.1 Flash-Lite</h1>
<p class="sub">Protocol v2, option B &middot; reused MPBench v4 split (replication evidence) &middot; 24 groups &middot; judge: GPT-4o-mini</p>
<p class="part"><b>Part A &mdash; all three answer models</b></p>{t1}{FIG1}{t2}{t3}{t4}{PART_B}
<p class="note">Claude Haiku answers are sent without temperature (the model does not accept it) and with reasoning
disabled, 200 tokens, same prompts (protocol revisions 8&ndash;9). GPT-4o-mini: temperature 0, 200 tokens.
Gemini 3.1 Flash-Lite (protocol revisions 10&ndash;11): temperature 0, reasoning disabled, 200 tokens, same prompts;
11.2% of its answers reached the 200-token limit (GPT-4o-mini 1.5%, Claude Haiku 1.2%).
Rows: GPT-4o-mini 3,655,680; Claude Haiku 212,520; Gemini 212,520. Source: analysis/tables.md, appendix.md (A13), analysis.json;
analysis_gemini/appendix.md (A14), extra_backbone_analysis.json.</p>
</body></html>"""
(HERE / "tables.html").write_text(html)
print("ok")
