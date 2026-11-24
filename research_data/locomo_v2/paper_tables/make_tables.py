"""Paper-style LoCoMo result tables, in the layout of the MPBench Option B tables
(research_data/protocol_v2_optionB_run_v1/paper_tables/make_tables.py on main).

Reads only finished analysis outputs (no API, no recomputation):
  run/analysis.json                                   frozen LoCoMo v2 primary analysis (curves, hypotheses)
  supp_published/run_supp/supp_baselines_analysis.json supplementary published-baseline analysis (all 11 methods)
  <main>/research_data/protocol_v2_optionB_run_v1/analysis/analysis.json  MPBench GPT-4o-mini (comparison table only)
Writes fig1_tradeoff.svg and tables.html (printed to PDF with headless Edge/Chrome).

  python make_tables.py
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
L2 = HERE.parent
F = json.load(open(L2 / "run/analysis.json", encoding="utf8"))
P = json.load(open(L2 / "supp_published/run_supp/supp_baselines_analysis.json", encoding="utf8"))
PD = json.load(open(L2 / "supp_published/run_supp/supp_baselines_analysis_dev.json", encoding="utf8"))
MP = json.load(open(Path("C:/Users/HP/Documents/sdp/research_data/protocol_v2_optionB_run_v1/analysis/analysis.json"),
                    encoding="utf8"))

LABEL = {"static": "No defence", "a_memguard": "A-MemGuard", "memlineage": "MemLineage",
         "llm_sanitiser": "LLM Sanitiser", "randec": "RandEC", "R": "R", "C": "C", "M": "M",
         "S": "S (ours)", "SL": "SL (ours)", "S2-ID": "S2-ID (ours)"}
GROUPS = [["static"], ["a_memguard", "memlineage", "llm_sanitiser", "randec"], ["R", "C", "M"], ["S", "SL", "S2-ID"]]
GROUPS_B = [["static"], ["R", "C", "M"], ["S", "SL", "S2-ID"]]  # frozen v2 families: published defences not run there
OURS = {"S", "SL", "S2-ID"}
SHAPES = (("1s", "1 session"), ("2s", "2 sessions"), ("quarter", "&frac14; of sessions"), ("spread", "all sessions"))


def pv(shape, metric):  # supplementary table (all 11 methods, loc family, A1 audits)
    def g(m):
        x = P["table"].get(f"{shape}|{m}", {}).get(metric)
        return None if x is None else 100 * x
    return g


def fv(cell, metric):  # frozen v2 curves
    def g(m):
        c = F["curves"].get(f"{cell}|{m}")
        return None if c is None or metric not in c else 100 * c[metric]["mean"]
    return g


def mv(cell, metric):  # MPBench GPT-4o-mini
    mp = {"static": "static"}

    def g(m):
        try:
            return 100 * MP["cells"][cell][mp.get(m, m)][metric]["value"]
        except KeyError:
            return None
    return g


def cellhtml(v, base, lower_better, best):
    if v is None:
        return "<td>&ndash;</td>"
    s = f"{v:.1f}"
    s = f"<b>{s}</b>" if best else s
    if base is None:
        return f"<td>{s}</td>"
    d = round(round(v, 1) - round(base, 1), 1)
    if abs(d) < 0.05:
        tag = '<span class="eq">&plusmn;0.0</span>'
    else:
        good = (d < 0) == lower_better
        tag = f'<span class="{"good" if good else "bad"}">{"&darr;" if d < 0 else "&uarr;"}{abs(d):.1f}</span>'
    return f"<td>{s}<sub>{tag}</sub></td>"


def table(caption, head1, cols, groups=GROUPS, note="", wide=False):
    """cols: [(getter, lower_better, header)]; head1: [(label, span)]."""
    allm = [m for g in groups for m in g]
    best = []
    for get, lower, _ in cols:
        vs = [round(get(m), 1) for m in allm if get(m) is not None]
        best.append((min(vs) if lower else max(vs)) if vs else None)
    rows = []
    for gi, g in enumerate(groups):
        for m in g:
            sep = ' class="gsep"' if gi > 0 and m == g[0] else ""
            cls = ' class="ours"' if m in OURS else ""
            tds = []
            for (get, lower, _), b in zip(cols, best):
                v = get(m)
                base = None if m == "static" else get("static")
                tds.append(cellhtml(v, base, lower, v is not None and round(v, 1) == b))
            rows.append(f"<tr{sep}><td{cls}>{LABEL[m]}</td>{''.join(tds)}</tr>")
    h1 = "".join(f'<th colspan="{n}" class="grp">{t}</th>' for t, n in head1)
    h2 = "".join(f"<th>{c[2]}</th>" for c in cols)
    return f"""<div class="tab{' wide' if wide else ''}"><p class="cap">{caption}</p><table>
<thead><tr><th rowspan="2" class="lh">Method</th>{h1}</tr><tr>{h2}</tr></thead>
<tbody>{''.join(rows)}</tbody></table>{note}</div>"""


SUB = ("Subscripts: change against No defence (<span class=good>green</span> = better, <span class=bad>red</span> = worse); "
       "best per column in <b>bold</b>.")

# ----------------------------------------------------------------------------- Table 1: localized (1s)
t1 = table("<b>Table 1:</b> Defensive performance against the <i>localized</i> hijack on LoCoMo (the attacker's 8 poison "
           "turns in one session; 2 of them detected, oracle audits A1), 8 held-out conversations, GPT-4o-mini. Values in %, "
           "mean over conversations. Attack metrics: lower is better (&darr;); utility: higher is better (&uarr;). " + SUB,
           [("Attack (&darr;)", 2), ("Usefulness (&uarr;)", 2)],
           [(pv("1s", "asr"), True, "ASR"), (pv("1s", "value_exposure"), True, "Value exp."),
            (pv("1s", "acc_U_out"), False, "Key-evidence acc."), (pv("1s", "acc_U_all"), False, "Net utility")],
           note='<p class="tnote"><b>Methods.</b> <b>No defence</b>: static top-10 retrieval over conversation turns; audit '
                'results are not used. <b>R</b> (record-only): withholds only the turn an audit found unsafe. <b>C</b> '
                '(contextual reputation): penalises the unsafe speaker\'s turns in the same conversation. <b>M</b> '
                '(multi-scope reputation): the maximum of the session, conversation and speaker penalties. <b>S</b> (ours, '
                'selective propagation): extends distrust only as far as the audit evidence supports (session after 1 unsafe '
                'audit, conversation after 2 spanning two sessions). <b>SL</b> (ours): S + content lineage (withholds '
                'near-copies, MiniLM cosine &ge; 0.8, of an audited-unsafe turn). <b>S2-ID</b> (ours, hybrid): SL + '
                'MemLineage\'s sensitive-action gate; LoCoMo has no sensitive-action questions, so S2-ID &equiv; SL here. '
                'Published defences (A-MemGuard, MemLineage, LLM Sanitiser, RandEC) filter the no-defence retrieval with no '
                'refill and use no audits; A-MemGuard uses one draw at its repository temperature 1.0; the LLM Sanitiser keeps '
                'its rewrites. MemLineage and RandEC are inactive on LoCoMo (no sensitive actions; no flagged turns).<br>'
                '<b>Metrics.</b> <b>ASR</b>: the injected false value appears (word-bounded) in the answer, over eligible '
                'targets whose poison turn was not audited unsafe. <b>Value exp.</b>: the injected value is still in the '
                'answer context. <b>Key-evidence acc.</b>: judge accuracy on questions whose evidence is the attacked speaker\'s '
                'genuine turns outside the hijacked window (the evidence C and M discard). <b>Net utility</b>: judge accuracy '
                'over all questions. Mapping: turn = memory, speaker = contributor, session = batch, conversation = context. '
                f'Dev conversations (conv-48/49, reported separately): ASR no defence {100*PD["table"]["1s|static"]["asr"]:.1f}, '
                f'LLM Sanitiser {100*PD["table"]["1s|llm_sanitiser"]["asr"]:.1f}, A-MemGuard '
                f'{100*PD["table"]["1s|a_memguard"]["asr"]:.1f}, S {100*PD["table"]["1s|S"]["asr"]:.1f}.</p>')

# ----------------------------------------------------------------------------- Figure 1
PTS = [(["S", "SL", "S2-ID"], "S, SL, S2-ID (ours)", "#0072B2", "o", 70),
       (["C", "M"], "C, M", "#E69F00", "^", 42),
       (["a_memguard"], "A-MemGuard", "#CC79A7", "D", 34),
       (["static", "memlineage", "randec", "R"], "No defence, MemLineage, RandEC, R", "#7a7a7a", "o", 60),
       (["llm_sanitiser"], "LLM Sanitiser", "#7B5EA7", "P", 60)]  # drawn last: it sits next to no defence
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"], "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e6",
                     "grid.linewidth": 0.6, "legend.frameon": False, "savefig.bbox": "tight"})
fig, axes = plt.subplots(1, 4, figsize=(7.4, 2.5), sharey=True)
for ax, (shape, title) in zip(axes, SHAPES):
    for ms, lab, c, mk, size in PTS:
        xs = [pv(shape, "asr")(m) for m in ms]
        ys = [pv(shape, "acc_U_all")(m) for m in ms]
        assert max(xs) - min(xs) < 1 and max(ys) - min(ys) < 1, (shape, ms)
        open_ = mk == "o" and c == "#7a7a7a"  # hollow grey circle so the sanitiser's cross stays visible on top
        ax.scatter([xs[0]], [ys[0]], s=size, marker=mk, zorder=4 if mk == "P" else 3, label=lab,
                   facecolor="none" if open_ else c, edgecolor=c if open_ else "white", linewidth=1.1 if open_ else 0.6)
    ax.set_title(title.replace("&frac14;", "¼"), fontsize=9)
    ax.set_xlim(-4, 55)
    ax.set_ylim(27, 50)
    ax.set_xlabel("ASR (%) ↓", fontsize=8.5)
axes[0].set_ylabel("Net utility (%) ↑")
axes[0].annotate("better", xy=(4, 47.5), xytext=(18, 40), fontsize=7.4, color="#0072B2",
                 arrowprops=dict(arrowstyle="->", color="#0072B2", lw=0.8))
axes[1].legend(loc="upper center", bbox_to_anchor=(1.1, -0.25), ncol=3, fontsize=7.6)
fig.savefig(HERE / "fig1_tradeoff.svg")
FIG1 = """<div class="fig"><img src="fig1_tradeoff.svg" alt="Figure 1"><p class="cap"><b>Figure 1:</b> Attack success against
net utility for the four hijack shapes (Table 2), GPT-4o-mini. Top left is best. With one hijacked session, S, SL and S2-ID remove
the attack and keep the utility of no defence; C and M also remove it but lose about 16 points. As the poison spreads over more
sessions, the audits justify wider distrust and S moves towards C and M. The published defences keep utility in every shape;
A-MemGuard cuts ASR by about 30% relative, the LLM Sanitiser barely acts.</p></div>"""

# ----------------------------------------------------------------------------- Table 2: hijack shapes
t2 = table("<b>Table 2:</b> Target ASR and net utility as the poison spreads: the attacker's 8 poison turns are placed in "
           "1 session, 2 sessions, a quarter of the sessions, or all sessions (2 turns detected, A1). " + SUB,
           [("ASR (&darr;)", 4), ("Net utility (&uarr;)", 4)],
           [(pv(s, "asr"), True, t) for s, t in SHAPES] + [(pv(s, "acc_U_all"), False, t) for s, t in SHAPES], wide=True)

# ----------------------------------------------------------------------------- Table 3: hypotheses (LoCoMo vs MPBench)
HYP = [("H1 vs C", "S keeps the attacked speaker's out-of-window evidence C discards, equally safe"),
       ("H1 vs M", "the same, against M"),
       ("H2", "S as safe as M when the poison spans every session"),
       ("H3", "S below every published defence (ASR)"),
       ("H4", "S2-ID below S under Sybil / laundering"),
       ("H5", "SL cuts relay exposure, no utility loss"),
       ("H6 vs C", "S more useful to a falsely accused speaker"),
       ("H6 vs M", "the same, against M")]


def fmt_est(e):
    n = round(100 * e)
    return f' <span class="est">({"0" if n == 0 else f"{n:+d}"})</span>'


hrows = []
for name, desc in HYP:
    h = F["hypotheses"].get(name)
    if h is None:
        loc = '<td><span class="eq">n/a&Dagger;</span></td>'
    else:
        part = max(h["parts"], key=lambda p: p["estimate"]) if name == "H3" else h["parts"][0]
        loc = (f'<td>{"<span class=good>&#10003;</span>" if h["reject"] else "<span class=bad>&#10007;</span>"}'
               f'{fmt_est(part["estimate"])}</td>')
    c = MP["hypotheses"]["contrasts"].get(name)
    est = ""
    if c and c.get("components"):
        comp = max(c["components"], key=lambda x: x["estimate"]) if name == "H3" else c["components"][0]
        if comp.get("estimate") is not None:
            est = fmt_est(comp["estimate"])
    ok = bool(c and c.get("reject"))
    mpb = f'<td>{"<span class=good>&#10003;</span>" if ok else "<span class=bad>&#10007;</span>"}{est}</td>'
    hrows.append(f"<tr><td>{name}</td><td class='desc'>{desc}</td>{loc}{mpb}</tr>")
t3 = f"""<div class="tab half"><p class="cap"><b>Table 3:</b> Pre-registered hypotheses on LoCoMo (frozen protocol v2;
exact sign-flip tests over 8 held-out conversations, Holm over 7 primary contrasts) next to the same hypotheses on MPBench
(GPT-4o-mini, Holm over 8). Primary estimate in points in brackets; for H3, the estimate against the closest published
defence in the frozen test.</p>
<table><thead><tr><th class="lh">Contrast</th><th class="lh">Claim</th><th>LoCoMo</th><th>MPBench</th></tr></thead>
<tbody>{''.join(hrows)}</tbody></table>
<p class="tnote">LoCoMo cells: H1, H3 localized (1 session); H2 all sessions; H5 relay r = 1; H6 two false flags in one session
(the smallest false accusation that can cause harm on LoCoMo; MPBench's single false positive cannot separate the rules, hence
&#10007;). H3 in the frozen test compares S with MemLineage and RandEC, which are inactive on LoCoMo; the supplementary comparison
with A-MemGuard and the LLM Sanitiser is in Table 4 (descriptive). &Dagger; H4 is not testable on LoCoMo: no sensitive-action
questions, so S2-ID &equiv; SL by construction.</p></div>"""

# ----------------------------------------------------------------------------- Table 4: S - X contrasts
CN = {c["contrast"].split(" - ")[1] + "|" + c["shape"] + "|" + c["metric"]: c for c in P["contrasts"]}
XS = ["static", "a_memguard", "memlineage", "llm_sanitiser", "randec", "C", "M"]


def ccell(x, shape, metric):
    c = CN.get(f"{x}|{shape}|{metric}")
    if c is None:
        return "<td>&ndash;</td>"
    d = 100 * c["mean"]
    k = c["S_better_in"]
    if abs(d) < 0.05:
        cls = "eq"
    else:
        cls = "good" if (d < 0) == (metric == "asr") else "bad"
    s = f"{d:+.1f}".replace("-", "&minus;")
    return f'<td><span class="{cls}">{s}</span><sub><span class="kk">{k}</span></sub></td>'


crows = []
for i, x in enumerate(XS):
    sep = ' class="gsep"' if x in ("a_memguard", "C") else ""
    tds = [ccell(x, s, "asr") for s, _ in SHAPES] + [ccell(x, s, "acc_U_all") for s, _ in SHAPES]
    crows.append(f"<tr{sep}><td>S &minus; {LABEL[x]}</td>{''.join(tds)}</tr>")
h2 = "".join(f"<th>{t}</th>" for _, t in SHAPES) * 2
t4 = f"""<div class="tab wide"><p class="cap"><b>Table 4:</b> S against every baseline, per hijack shape (points; mean
paired difference over 8 held-out conversations). Subscript: conversations in which S is strictly better (k/8).
<span class=good>Green</span> = S better, <span class=bad>red</span> = S worse. Supplementary and descriptive (pre-registered;
no multiplicity control); exact sign-flip 95% intervals are in the results report.</p><table>
<thead><tr><th rowspan="2" class="lh">Contrast</th><th colspan="4" class="grp">&Delta; ASR (&darr; favours S)</th>
<th colspan="4" class="grp">&Delta; Net utility (&uarr; favours S)</th></tr><tr>{h2}</tr></thead>
<tbody>{''.join(crows)}</tbody></table>
<p class="tnote">Against A-MemGuard on one session: &Delta;ASR &minus;33.8 [&minus;41.0, &minus;25.8], &Delta;net utility +2.5
[&minus;0.6, +6.3]. A k/8 of 0/8 with a difference of 0.0 means ties (e.g. S and C both reach 0% ASR on one session).</p></div>"""

# ----------------------------------------------------------------------------- Table 5: MPBench vs LoCoMo
t5 = table("<b>Table 5:</b> Generalization of the localized result: MPBench (GPT-4o-mini, 24 groups; Original SAFE-Mem as the "
           "base) next to LoCoMo (GPT-4o-mini, 8 held-out conversations, one hijacked session; no defence as the base). "
           "The attack metrics differ (MPBench: the answer acts on a planted instruction; LoCoMo: the injected false value is "
           "restated), so compare changes and rankings, not levels. " + SUB.replace("No defence", "the base"),
           [("MPBench", 2), ("LoCoMo", 2)],
           [(mv("localized", "target_asr"), True, "Target ASR"), (mv("localized", "strict_utility"), False, "Strict utility"),
            (pv("1s", "asr"), True, "ASR"), (pv("1s", "acc_U_all"), False, "Net utility")],
           note='<p class="tnote">Same ranking on both benchmarks: S &asymp; C/M &lt; A-MemGuard &lt; LLM Sanitiser &le; '
                'base on attack success, and among the defences that cut it only S keeps the base utility. A-MemGuard gives '
                'a partial cut at a small utility cost on both; the LLM Sanitiser, built for instruction-like poison, does '
                'less against LoCoMo\'s factual misinformation. MemLineage acts on MPBench\'s sensitive actions and is '
                'inactive on LoCoMo.</p>')

# ----------------------------------------------------------------------------- Part B: frozen v2 families
ADV = [("sybil|k2|A1", "asr", "Sybil k=2"), ("sybil|k4|A1", "asr", "Sybil k=4"), ("shift|2s|O", "asr", "Shift"),
       ("relay|r0.5|A1", "relay_asr", "Relay r=.5&dagger;"), ("relay|r1.0|A1", "relay_asr", "Relay r=1&dagger;"),
       ("fn20|1s|A1", "asr", "Miss 20% (1 s.)"), ("fn20|spread|A1", "asr", "Miss 20% (all s.)")]
t6 = table("<b>Table 6a:</b> Adaptive attacks and imperfect audits, ASR (%, &darr;). <b>Sybil k</b>: the poison turns are "
           "dealt over the hijacked speaker and k&minus;1 fresh identities. <b>Shift</b> (audit-aware): 2 poison turns in the "
           "audited session, 6 in a second session the audits do not reach. <b>Relay r</b>: a fraction r of the poison turns "
           "gets a verbatim copy of unknown origin. <b>Miss 20%</b>: each true detection is missed with probability 0.2. " + SUB,
           [("Adaptive attacks", 5), ("Imperfect audits", 2)], [(fv(c, k), True, h) for c, k, h in ADV],
           groups=GROUPS_B, wide=True,
           note='<p class="tnote">&dagger; Relay ASR: targets whose original poison turn is audited unsafe and that have an '
                'unknown-origin copy.</p>')
t6 += table(f"<b>Table 6b:</b> The same conditions, net utility (%, &uarr;). {SUB}",
            [("Adaptive attacks", 5), ("Imperfect audits", 2)],
            [(fv(c, "acc_U_all"), False, h.replace("&dagger;", "")) for c, _, h in ADV], groups=GROUPS_B, wide=True)
t7 = table("<b>Table 7:</b> Review dilution and harm to innocent speakers. <b>A2</b>: the two detections plus 10 random "
           "reviews of the attacked speaker's turns that come back safe. <b>Framing</b> (no attack): genuine turns of a speaker "
           "are falsely flagged unsafe, 1 flag, 2 flags in one session (2 in 1 s.), or 2 flags in two sessions (2 in 2 s.); the "
           "metric is the accused speaker's utility over all of its evidence. " + SUB,
           [("A2 review dilution", 3), ("Framing: accused speaker's utility (&uarr;)", 3)],
           [(fv("loc|1s|A2", "asr"), True, "ASR 1 s. &darr;"), (fv("loc|spread|A2", "asr"), True, "ASR all s. &darr;"),
            (fv("loc|1s|A2", "acc_U_out"), False, "Key-ev. acc. 1 s. &uarr;"),
            (fv("frame|fp1|F", "acc_U_ext"), False, "1 flag"), (fv("frame|fp2c|F", "acc_U_ext"), False, "2 in 1 s."),
            (fv("frame|fp2s|F", "acc_U_ext"), False, "2 in 2 s.")], groups=GROUPS_B, wide=True)
WHY = """<div class="why"><b>Part B &mdash; frozen LoCoMo v2 conditions.</b> The tables below come from the frozen v2 run
(pre-registered protocol, run once). The published defences were added afterwards, as a pre-registered supplement, on the four
hijack shapes only (Part A): they filter each retrieved context without audits, so their behaviour does not depend on how the
attacker spreads identities, relays or audits, as on MPBench, where their values are identical in every adaptive column.</div>"""

CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: "Times New Roman", Times, serif; font-size: 10.5pt; color: #000; }
h1 { font-size: 14pt; text-align: center; margin: 0 0 2pt; } .sub { text-align: center; font-size: 9.5pt; margin: 0 0 10pt; color: #333; }
.tab { margin: 0 auto 14pt; page-break-inside: avoid; } .cap { margin: 0 0 4pt; line-height: 1.25; text-align: justify; }
table { border-collapse: collapse; margin: 0 auto; border-top: 1.6pt solid #000; border-bottom: 1.6pt solid #000; }
thead tr:last-child th { border-bottom: 1pt solid #000; } th, td { padding: 1.2pt 7pt; text-align: center; white-space: nowrap; }
thead { background: #f2f2f2; } th.grp { border-bottom: 0.6pt solid #000; } th.lh { text-align: left; vertical-align: middle; }
td:nth-child(1) { text-align: left; }
tbody { border-top: 1pt solid #000; } tr.gsep td { border-top: 0.4pt dotted #999; }
td.ours { font-weight: bold; } sub { font-size: 7.5pt; vertical-align: -1.5pt; margin-left: 1pt; }
.good { color: #1b8a7a; } .bad { color: #c62828; } .eq { color: #888; } .est { color: #555; font-size: 9pt; } .kk { color: #555; }
.half td:first-child { text-align: left; } td.desc { text-align: left; white-space: normal; max-width: 250pt; font-size: 9.5pt; }
.tnote { font-size: 8.6pt; line-height: 1.28; text-align: justify; margin: 4pt 0 0; color: #222; }
.why { border: 0.8pt solid #1b8a7a; background: #f3faf8; padding: 6pt 8pt; margin: 0 0 12pt; font-size: 9.5pt; line-height: 1.3; text-align: justify; }
.part { font-size: 11pt; margin: 4pt 0 6pt; }
.pb { page-break-before: always; }
.wide table { font-size: 9pt; } .wide th, .wide td { padding: 1.2pt 4.5pt; }
.fig { margin: 6pt auto 16pt; page-break-inside: avoid; text-align: center; } .fig img { width: 100%; }
.fig .cap { text-align: justify; }
.note { font-size: 9pt; color: #333; margin-top: 6pt; line-height: 1.3; }
"""
html = f"""<!doctype html><html><head><meta charset="utf-8"><title>SAFE-Mem LoCoMo results</title><style>{CSS}</style></head><body>
<h1>SAFE-Mem: results on LoCoMo (GPT-4o-mini)</h1>
<p class="sub">LoCoMo protocol v2 (frozen) + pre-registered published-baseline supplement &middot; 8 held-out conversations
&middot; answer model and judge: GPT-4o-mini</p>
<p class="part"><b>Part A &mdash; all eleven methods</b></p>{t1}{FIG1}{t2}{t3}{t4}{t5}
<div class="pb"></div>{WHY}{t6}{t7}
<p class="note">GPT-4o-mini at temperature 0 for answers and judgments. Each value: mean over 8 held-out conversations of
5 draws &times; 2 orientations. Spend: v2 run $9.55; supplement $19.56. Sources: locomo_v2/run/analysis.json and
supp_baselines_analysis.json (each run once); MPBench: protocol_v2_optionB_run_v1/analysis/analysis.json.</p>
</body></html>"""
(HERE / "tables.html").write_text(html, encoding="utf8")
print("ok")
