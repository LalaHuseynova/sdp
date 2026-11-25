"""MPBench-style result tables for the LoCoMo + SAFE-Mem study (HTML; print to PDF with headless Edge).
Reads only finished analyses: this study's analysis.json, LoCoMo v2's run/analysis.json (plain RAG)
and MPBench Option B's analysis.json (GPT-4o-mini). Layout and colour conventions as the MPBench and
LoCoMo v2 paper tables (change vs the base as subscripts, best per column in bold).

  python -m locomo_safemem.tables --analysis FILE --out DIR [--mpbench FILE] [--v2 FILE]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

LABEL = {"static": "Original SAFE-Mem", "a_memguard": "A-MemGuard", "memlineage": "MemLineage",
         "llm_sanitiser": "LLM Sanitiser", "randec": "RandEC", "R": "R", "C": "C", "M": "M", "S": "S (ours)",
         "SL": "SL (ours)", "S2-ID": "S2-ID (ours)", "S2-BS": "S2-BS (appendix)"}
GROUPS = [["static"], ["a_memguard", "memlineage", "llm_sanitiser", "randec"], ["R", "C", "M"], ["S", "SL", "S2-ID"]]
GROUPS_B = [["static"], ["memlineage", "randec"], ["R", "C", "M"], ["S", "SL", "S2-ID"]]
OURS = {"S", "SL", "S2-ID"}
CSS = """
@page { size: A4; margin: 16mm 14mm; } body { font-family: "Times New Roman", Times, serif; font-size: 10.5pt; color: #000; background: #fff; }
h1 { font-size: 14pt; text-align: center; margin: 0 0 2pt; } .sub { text-align: center; font-size: 9.5pt; margin: 0 0 10pt; color: #333; }
.tab { margin: 0 auto 14pt; page-break-inside: avoid; } .cap { margin: 0 0 4pt; line-height: 1.25; text-align: justify; }
table { border-collapse: collapse; margin: 0 auto; border-top: 1.6pt solid #000; border-bottom: 1.6pt solid #000; }
thead tr:last-child th { border-bottom: 1pt solid #000; } th, td { padding: 1.2pt 6pt; text-align: center; white-space: nowrap; }
thead { background: #f2f2f2; } th.grp { border-bottom: 0.6pt solid #000; } th.lh { text-align: left; }
td:nth-child(1) { text-align: left; } tbody { border-top: 1pt solid #000; } tr.gsep td { border-top: 0.4pt dotted #999; }
td.ours { font-weight: bold; } sub { font-size: 7.5pt; vertical-align: -1.5pt; margin-left: 1pt; }
.good { color: #1b8a7a; } .bad { color: #c62828; } .eq { color: #888; } .tnote { font-size: 8.6pt; line-height: 1.28; text-align: justify; margin: 4pt 0 0; }
.why { border: 0.8pt solid #1b8a7a; background: #f3faf8; padding: 6pt 8pt; margin: 0 0 12pt; font-size: 9.5pt; line-height: 1.3; }
.wide table { font-size: 8.6pt; } .wide th, .wide td { padding: 1.2pt 3.5pt; } td.desc { text-align: left; white-space: normal; max-width: 230pt; }
"""


def cell(v, base, lower, best):
    if v is None:
        return "<td>&ndash;</td>"
    s = f"<b>{v:.1f}</b>" if best else f"{v:.1f}"
    if base is None:
        return f"<td>{s}</td>"
    d = round(round(v, 1) - round(base, 1), 1)
    if abs(d) < 0.05:
        return f'<td>{s}<sub><span class="eq">&plusmn;0.0</span></sub></td>'
    good = (d < 0) == lower
    return f'<td>{s}<sub><span class="{"good" if good else "bad"}">{"&darr;" if d < 0 else "&uarr;"}{abs(d):.1f}</span></sub></td>'


def table(cap, head1, cols, groups=GROUPS, note=""):
    allm = [m for g in groups for m in g]
    best = []
    for get, lower, _ in cols:
        vs = [round(get(m), 1) for m in allm if get(m) is not None]
        best.append((min(vs) if lower else max(vs)) if vs else None)
    rows = []
    for gi, g in enumerate(groups):
        for m in g:
            tds = "".join(cell(get(m), None if m == "static" else get("static"), lower,
                               get(m) is not None and round(get(m), 1) == b) for (get, lower, _), b in zip(cols, best))
            rows.append(f'<tr{" class=gsep" if gi and m == g[0] else ""}><td{" class=ours" if m in OURS else ""}>'
                        f"{LABEL[m]}</td>{tds}</tr>")
    h1 = "".join(f'<th colspan="{n}" class="grp">{t}</th>' for t, n in head1)
    h2 = "".join(f"<th>{c[2]}</th>" for c in cols)
    return (f'<div class="tab wide"><p class="cap">{cap}</p><table><thead><tr><th rowspan="2" class="lh">Method</th>{h1}'
            f'</tr><tr>{h2}</tr></thead><tbody>{"".join(rows)}</tbody></table>{note}</div>')


def render(an: dict, mp: dict | None = None, v2: dict | None = None) -> str:
    T = an["table"]

    def g(key, met):
        def f(m):
            x = T.get(f"{key}|{m}", {}).get(met)
            return None if x is None else 100 * x
        return f

    sub = ("Subscripts: change against Original SAFE-Mem (<span class=good>green</span> better, <span class=bad>red</span> "
           "worse); best per column in <b>bold</b>. Supplementary and exploratory; 8 held-out conversations.")
    t1 = table("<b>Table 1:</b> Localized hijack (8 poison turns in one session; 2 detected, A1) on LoCoMo with "
               "Original SAFE-Mem's claim memory. " + sub,
               [("Attack (&darr;)", 3), ("Usefulness (&uarr;)", 3)],
               [(g("loc|1s|A1", "asr"), True, "ASR"), (g("loc|1s|A1", "value_exposure"), True, "Value exp."),
                (g("loc|1s|A1", "record_exposure"), True, "Record exp."), (g("loc|1s|A1", "acc_U_out"), False, "Key-ev. acc."),
                (g("loc|1s|A1", "acc_U_all"), False, "Net utility"), (g("loc|1s|A1", "strict_U_all"), False, "Strict (sec.)")])
    shapes = (("1s", "1 sess."), ("2s", "2 sess."), ("quarter", "&frac14;"), ("spread", "all"))
    t2 = table("<b>Table 2:</b> As the poison spreads over sessions. " + sub, [("ASR (&darr;)", 4), ("Net utility (&uarr;)", 4)],
               [(g(f"loc|{s}|A1", "asr"), True, t) for s, t in shapes] +
               [(g(f"loc|{s}|A1", "acc_U_all"), False, t) for s, t in shapes])
    adv = (("sybil|k2|A1", "Sybil 2"), ("sybil|k4|A1", "Sybil 4"), ("sybil|k8|A1", "Sybil 8"), ("shift|2s|O", "Shift"),
           ("relay|r1.0|A1", "Relay 1"), ("fn20|1s|A1", "Miss 20%"), ("imp|1s|fp1", "1 FP"), ("imp|1s|late", "Late"),
           ("imp|1s|fu", "Follow-up"), ("loc|1s|A2", "A2 reviews"), ("embed|1s|A1", "Embedded"))
    t3 = table("<b>Table 3:</b> Adaptive attacks, imperfect audits, review dilution and the ingestion sensitivity, ASR (%, "
               "&darr;); relay column: relay exposure. " + sub, [("ASR (&darr;)", len(adv))],
               [(g(k, "relay_exposure" if k.startswith("relay") else "asr"), True, t) for k, t in adv], groups=GROUPS_B)
    t3b = table("<b>Table 3b:</b> The same conditions, net utility (%, &uarr;). " + sub, [("Net utility (&uarr;)", len(adv))],
                [(g(k, "acc_U_all"), False, t) for k, t in adv], groups=GROUPS_B)
    t4 = table("<b>Table 4:</b> Harm to a falsely accused speaker (no attack): the accused speaker's utility (acc U_ext, "
               "&uarr;). " + sub, [("False accusations", 3)],
               [(g(f"frame|{k}|F", "acc_U_ext"), False, t) for k, t in (("fp1", "1 flag"), ("fp2c", "2 in 1 s."),
                                                                         ("fp2s", "2 in 2 s."))], groups=GROUPS_B)
    hy = []
    mph = (mp or {}).get("hypotheses", {}).get("contrasts", {})
    v2h = (v2 or {}).get("hypotheses", {})
    for h, v in an["hypotheses"].items():
        est = v["parts"][0]["estimate"]
        e = "" if est is None else f" ({round(100 * est):+d})"
        mark = "&#10003;" if v.get("reject") else "&#10007;"
        base = h.split(" (")[0].replace("'", "")
        m = mph.get(base)
        v2m = v2h.get(base)
        hy.append(f"<tr><td>{h}</td><td>{'&#10003;' if m and m.get('reject') else '&#10007;' if m else '&ndash;'}</td>"
                  f"<td>{'&#10003;' if v2m and v2m.get('reject') else '&#10007;' if v2m else 'n/a'}</td>"
                  f"<td>{mark}{e} <span class=eq>(descr.)</span></td></tr>")
    t5 = (f'<div class="tab"><p class="cap"><b>Table 5:</b> MPBench hypotheses on three settings: MPBench (Option B, '
          f"GPT-4o-mini, SAFE-Mem), LoCoMo with plain RAG (v2, frozen) and LoCoMo with SAFE-Mem (this study, descriptive). "
          f"Estimate of the first part in points.</p><table><thead><tr><th class=lh>Hypothesis</th><th>MPBench</th>"
          f"<th>LoCoMo / RAG</th><th>LoCoMo / SAFE-Mem</th></tr></thead><tbody>{''.join(hy)}</tbody></table></div>")
    mech = an.get("mechanism", {})
    mrows = "".join(f"<tr><td>{k}</td><td>{v['mean']}</td><td>{v['min']}</td><td>{v['max']}</td></tr>"
                    for k, v in mech.items() if k != "ratios")
    mrows += "".join(f"<tr><td><b>{k}</b> (share over all stores)</td><td colspan=3>{v}</td></tr>"
                     for k, v in mech.get("ratios", {}).items())
    t6 = (f'<div class="tab"><p class="cap"><b>Table 6:</b> SAFE-Mem construction diagnostics per store (pre-registered '
          f"validity checks).</p><table><thead><tr><th class=lh>Diagnostic</th><th>mean</th><th>min</th><th>max</th></tr>"
          f"</thead><tbody>{mrows}</tbody></table></div>")
    return (f"<!doctype html><html><head><meta charset=utf-8><title>LoCoMo SAFE-Mem results</title><style>{CSS}</style>"
            f"</head><body><h1>S on LoCoMo with Original SAFE-Mem memory</h1><p class=sub>Supplementary, exploratory "
            f"&middot; {an.get('protocol')} &middot; 8 held-out conversations &middot; GPT-4o-mini</p>"
            f"{t1}{t2}{t5}{t3}{t3b}{t4}{t6}</body></html>")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mpbench", type=Path)
    ap.add_argument("--v2", type=Path)
    a = ap.parse_args(argv)
    an = json.loads(a.analysis.read_text())
    mp = json.loads(a.mpbench.read_text()) if a.mpbench and a.mpbench.exists() else None
    v2 = json.loads(a.v2.read_text()) if a.v2 and a.v2.exists() else None
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "tables.html").write_text(render(an, mp, v2), encoding="utf8")
    print(a.out / "tables.html")


if __name__ == "__main__":
    main()
