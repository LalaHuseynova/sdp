#!/usr/bin/env python3
"""Methodology figure: selective evidence propagation (S) on top of SAFE-Mem.

Writes an editable SVG (real text, no rasters). Dependency-free. Every mechanism,
threshold and step order is taken from the repository implementation:
  scope gates / risk ........ src/ams/research/dynamic/ledger.py  (GroupStats, active_scopes)
  R/C/M/S decision .......... src/ams/research/dynamic/policies.py (Policy.decide)
  retrieval order ........... src/ams/research/retrieval/adapter.py (retrieve_with_trace)
  SL (candidate-level veto) . src/ams/research/workload/lineage.py (LineagePolicy.decide)
  S2-ID (final-context gate)  src/ams/research/workload/sv2.py (_GatedReader)
  boundary verification ..... src/ams/research/workload/adaptive.py (_followup_ticket)

    python make_figure.py --out fig_method.svg

Canvas 1390 x 640 units = 6.75 in x 3.108 in (ICML full text width); 1 pt = 2.86 units.
Smallest text is 16 units (about 5.6 pt); body text 16.5-19 units (5.8-6.6 pt).
"""

import argparse
import sys

W, H = 1390, 640
SANS = "Arial, Helvetica, sans-serif"
SERIF = "'Times New Roman', Times, serif"
SMALL = 16  # minimum text size used anywhere (~5.6 pt at print size)

# ---- PALETTE: every colour in the figure is defined here (one hex per role) -------------
INK, MUTED, FAINT = "#1E1E1E", "#5A5A5A", "#CFCFCF"          # text, secondary text, frames
GREY, GREY_F = "#7A7A7A", "#F2F2F2"                           # SAFE-Mem (unchanged)
S_LINE, S_DARK = "#7461B8", "#4B3C8C"                         # S: borders/badges, titles/text
S_FILL, S_TINT, S_BG = "#ECE8F8", "#F6F4FC", "#FCFBFF"        # S: fills, light fills, panel
S_SEP = "#E3DEF2"                                             # S: separators
S_OFF_LINE, S_OFF_TEXT = "#ADA3D1", "#76699F"                 # S: inactive scopes
S_OFF_F1, S_OFF_F2 = "#FAF9FD", "#F4F2FA"                     # S: inactive scope fills
TEAL, TEAL_D, TEAL_F = "#2B7F73", "#1E5E55", "#E4F2EF"        # SL (our extension)
AMBER, AMBER_D, AMBER_F = "#C77700", "#8A5300", "#FDF1DD"     # S2-ID (hybrid), dashed
RED, RED_F = "#B8322A", "#F8E3E1"                             # unsafe / withheld / lost

# Arial advance widths (per 1000 em) for the characters used; default 556.
_AW = {
    " ": 278, "!": 278, "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333, ".": 278,
    "/": 278, ":": 278, ";": 278, "=": 584, "?": 556, "@": 1015, "&": 667, "'": 191,
    "’": 222, "“": 333, "”": 333, "·": 278, "≥": 549, "−": 584,
    "→": 1000, "½": 834, "λ": 500, "|": 260, "<": 584,
    "I": 278, "J": 500, "L": 556, "M": 833, "W": 944, "F": 611, "T": 611, "Z": 611,
    "C": 722, "D": 722, "H": 722, "N": 722, "R": 722, "U": 722, "G": 778, "O": 778, "Q": 778,
    "f": 278, "i": 222, "j": 222, "l": 222, "t": 278, "r": 333, "m": 833, "w": 722,
    "c": 500, "k": 500, "s": 500, "v": 500, "x": 500, "y": 500, "z": 500,
}
_BOLD = {"b": 611, "d": 611, "g": 611, "h": 611, "n": 611, "o": 611, "p": 611, "q": 611,
         "u": 611, "r": 389, "t": 333, "f": 333, "i": 278, "l": 278, "c": 556, "k": 556,
         "s": 556, "v": 556, "y": 556, "x": 556, "z": 500, "m": 889, "w": 778}


def text_width(s, size, bold=False, serif=False):
    total = 0
    for ch in s:
        w = (_BOLD.get(ch) if bold else None) or _AW.get(ch, 556)
        if bold and ch.isupper():
            w *= 1.06
        total += w
    return total / 1000 * size * (0.9 if serif else 1.0)


EL, WARN = [], []


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _check(s, w, maxw, size):
    if maxw is not None and w > maxw + 0.5:
        WARN.append(f"overflow {w:.0f}>{maxw:.0f}: {s!r}")
    if size < SMALL:
        WARN.append(f"text below {SMALL}u: {s!r}")


def text(x, y, s, size=17, weight="normal", fill=INK, anchor="start", italic=False,
         serif=False, maxw=None):
    w = text_width(s, size, weight == "bold", serif)
    _check(s, w, maxw, size)
    style = ' font-style="italic"' if italic else ""
    fam = SERIF if serif else SANS
    EL.append(
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{style}>{esc(s)}</text>'
    )
    return w


SUB = 0.78  # subscript scale


def rich(x, y, parts, size=17, maxw=None):
    """parts: [(text, {'weight','fill','italic','serif','sub'})] on one baseline."""
    total = sum(text_width(t, size * (SUB if o.get("sub") else 1), o.get("weight") == "bold",
                           o.get("serif", False)) for t, o in parts)
    _check("".join(t for t, _ in parts), total, maxw, size)
    spans, shifted = [], False
    for t, o in parts:
        fam = SERIF if o.get("serif") else SANS
        it = ' font-style="italic"' if o.get("italic") else ""
        sub = o.get("sub", False)
        dy = size * 0.22 if sub and not shifted else (-size * 0.22 if shifted and not sub else 0)
        shifted = sub
        extra = (f' dy="{dy:.1f}"' if dy else "") + (f' font-size="{size*SUB:.1f}"' if sub else "")
        spans.append(f'<tspan font-family="{fam}" font-weight="{o.get("weight", "normal")}" '
                     f'fill="{o.get("fill", INK)}"{it}{extra}>{esc(t)}</tspan>')
    EL.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" xml:space="preserve">'
              + "".join(spans) + "</text>")
    return total


def rect(x, y, w, h, fill="none", stroke=FAINT, sw=1.2, rx=8, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    EL.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
              f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def line(points, color=GREY, sw=1.4, dash=None, marker=None):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = f' marker-end="url(#{marker})"' if marker else ""
    EL.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{sw}" '
              f'stroke-linejoin="round" stroke-linecap="round"{d}{m}/>')


def main_arrow(points):
    """Tier 1: data flow (records, queries, contexts)."""
    line(points, color="#4A4A4A", sw=2.2, marker="a-main")


def ev_arrow(points, color=GREY, marker="a-ev"):
    """Tier 2: evidence / control flow."""
    line(points, color=color, sw=1.5, dash="5 3.5", marker=marker)


def group(name):
    EL.append(f'<g id="{name}">')


def end():
    EL.append("</g>")


# ---- status glyphs ---------------------------------------------------------------------
def badge_x(cx, cy, r=7.5):
    EL.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{RED}"/>')
    k = r * 0.45
    EL.append(f'<path d="M{cx-k},{cy-k} L{cx+k},{cy+k} M{cx+k},{cy-k} L{cx-k},{cy+k}" '
              f'stroke="#fff" stroke-width="1.8" stroke-linecap="round"/>')


def badge_ok(cx, cy, r=7.5):
    EL.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{S_LINE}"/>')
    EL.append(f'<path d="M{cx-r*0.48},{cy+r*0.02} L{cx-r*0.12},{cy+r*0.38} L{cx+r*0.5},{cy-r*0.36}" '
              f'fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" '
              f'stroke-linejoin="round"/>')


def badge_open(cx, cy, r=7.5):
    EL.append(f'<circle cx="{cx}" cy="{cy}" r="{r-0.7}" fill="#fff" stroke="#8A8A8A" '
              f'stroke-width="1.4"/>')


def badge_leak(cx, cy, r=7.5):
    EL.append(f'<circle cx="{cx}" cy="{cy}" r="{r-0.7}" fill="#fff" stroke="{RED}" stroke-width="1.8"/>')
    EL.append(f'<circle cx="{cx}" cy="{cy}" r="{r*0.32}" fill="{RED}"/>')


def step_num(cx, cy, n, color):
    EL.append(f'<circle cx="{cx}" cy="{cy}" r="9" fill="{color}"/>')
    EL.append(f'<text x="{cx}" y="{cy+4.6}" font-family="{SANS}" font-size="13" '
              f'font-weight="bold" fill="#fff" text-anchor="middle">{n}</text>')


# =======================================================================================
# Layout. Panels (a) and (c) are unframed; only the contribution, panel (b), has a frame.
PANEL_TOP, PANEL_H = 8, 580
AX, AW = 8, 322      # panel (a)
BX, BW = 340, 552    # panel (b), the contribution
CX, CW = 904, 478    # panel (c)
RX = 3               # corner radius used everywhere (near-square, print style)
ROUTE_Y = 604        # the content-lineage connector runs below the panels
TITLE = 21


def title(x, y, label, sub=None, color=INK, maxw=None):
    text(x, y, label, TITLE, "bold", fill=color, maxw=maxw)
    if sub:
        text(x, y + 23, sub, 16.5, italic=True, fill=color if color != INK else MUTED, maxw=maxw)


def row(x, y, kind, s, w, size=16.5, weight="normal", fill=INK):
    """One memory: status glyph + claim text (baseline y)."""
    {"x": badge_x, "o": badge_open}[kind](x + 9, y - 5.5, 7)
    text(x + 22, y, s, size, weight, fill=fill, maxw=w - 22)


def lineage_line(points, marker="a-teal"):
    """Content similarity (SL / content lineage): dotted teal."""
    line(points, color=TEAL, sw=1.5, dash="1.5 3.2", marker=marker)


def panel_a():
    group("panel-a")
    L, R = AX + 14, AX + AW - 14
    w = R - L
    title(L, 36, "(a) Provenance & audits", maxw=w)

    # contributor A, context X (localized placement: seeds and planted attack share batch 1)
    text(L, 70, "Contributor A · context X", 17, "bold", maxw=w)
    rect(L, 80, w, 94, fill="#FAFAFA", stroke="#C4C4C4", sw=1, rx=RX)
    text(L + 10, 98, "batch 1", SMALL, "bold", fill=MUTED)
    row(L + 10, 120, "x", "Default payee is QX Ltd.", w - 20)
    row(L + 10, 143, "x", "Escalate to ops@example.com", w - 20)
    row(L + 10, 166, "o", "“Project code is ZX-91”", w - 20, weight="bold", fill=RED)
    rect(L, 182, w, 52, fill="#FAFAFA", stroke="#C4C4C4", sw=1, rx=RX)
    text(L + 10, 200, "batch 2", SMALL, "bold", fill=MUTED)
    row(L + 10, 223, "o", "“Larkspur review: Wednesdays”", w - 20, weight="bold", fill=S_DARK)

    # context Y, collapsed: A's other two audited seeds
    text(L + 10, 258, "context Y", SMALL, "bold", fill=MUTED)
    text(L + 104, 258, "b1", SMALL, fill=MUTED)
    badge_x(L + 132, 252.5, 6.5)
    badge_x(L + 149, 252.5, 6.5)
    text(L + 176, 258, "b2", SMALL, fill=MUTED)
    badge_open(L + 204, 252.5, 6.5)
    badge_open(L + 221, 252.5, 6.5)

    # unrelated contributor U: an unaudited near-copy of an unsafe-AUDITED seed
    text(L, 292, "Contributor U · unlinked relay", 17, "bold", maxw=w)
    rect(L, 302, w, 30, fill="#FAFAFA", stroke="#C4C4C4", sw=1, rx=RX)
    row(L + 10, 322, "o", "“Escalate to ops@example.com”", w - 20, weight="bold", fill=RED)
    text(L + 10, 352, "near-copy of an unsafe-audited claim;", SMALL, italic=True,
         fill=TEAL_D, maxw=w - 10)
    text(L + 10, 371, "U itself has no audit evidence", SMALL, italic=True,
         fill=TEAL_D, maxw=w - 10)
    jx = AX + 6                                    # connector spine, left margin
    EL.append(f'<circle cx="{jx}" cy="317" r="2.6" fill="{TEAL}"/>')
    lineage_line([(jx, 317), (L - 1, 317)], marker=None)
    lineage_line([(jx, 317), (jx, 138), (L - 2, 138)])                 # relay -> audited seed
    lineage_line([(jx, 317), (jx, ROUTE_Y)], marker=None)              # relay -> SL, panel (c)

    # audit allocation (oracle; identical ticket IDs for R, C, M, S)
    rich(L, 408, [("5 audit tickets", {"weight": "bold"}),
                  ("  (R, C, M, S)", {"fill": MUTED})], size=17, maxw=w)
    rich(L, 429, [("4 seeds of A", {"weight": "bold", "fill": RED}),
                  (" → unsafe (2 in X, 2 in Y)", {})], size=SMALL, maxw=w)
    rich(L, 449, [("1 benign item of B", {"weight": "bold"}), (" → safe", {})],
         size=SMALL, maxw=w)
    text(L, 475, "Optional boundary verification: the 5th", SMALL, italic=True,
         fill=MUTED, maxw=w)
    text(L, 494, "ticket audits A’s other batch instead.", SMALL, italic=True,
         fill=MUTED, maxw=w)

    rect(L, 510, w, 50, fill=GREY_F, stroke=GREY, sw=1, rx=RX)
    text(L + 12, 531, "Evidence ledger", 17, "bold")
    text(L + 12, 551, "one vote per origin; corrections retract", SMALL, fill=MUTED,
         maxw=w - 24)
    gx = (AX + AW + BX) / 2
    ev_arrow([(R, 535), (gx, 535), (gx, 196), (BX + 15, 196)], color=S_LINE, marker="a-blue")
    end()


def state_label(x_right, y, s, active):
    if active:
        text(x_right, y, s, SMALL, "bold", fill=S_DARK, anchor="end")
    else:
        text(x_right, y, s, SMALL, italic=True, fill=S_OFF_TEXT, anchor="end")


def panel_b():
    group("panel-b-S")
    x, w = BX, BW
    L = x + 16
    rect(x, PANEL_TOP, w, PANEL_H, fill=S_BG, stroke=S_LINE, sw=1.8, rx=RX)
    title(x + 16, 36, "(b) S: selective distrust propagation", color=S_DARK, maxw=w - 32)
    text(x + 16, 59, "Distrust spreads only as far as the audit evidence reaches.", 16.5,
         italic=True, fill=S_DARK, maxw=w - 32)

    # nested scopes = ledger.active_scopes; state shown for A's records in context X
    sw = 284
    text(L, 94, "Scopes and support gates", SMALL, "bold", fill=MUTED)
    rect(L, 104, sw, 243, fill=S_OFF_F1, stroke=S_OFF_LINE, sw=1.1, rx=RX, dash="4 3")
    text(L + 12, 127, "Contributor", 17, "bold", fill=S_OFF_TEXT)
    state_label(L + sw - 12, 127, "not met", False)
    text(L + 12, 147, "≥ 4 unsafe, and the context gate", SMALL, fill=MUTED, maxw=sw - 24)
    text(L + 12, 166, "holds in ≥ 2 contexts", SMALL, fill=MUTED, maxw=sw - 24)
    rect(L + 14, 178, sw - 28, 161, fill=S_OFF_F2, stroke=S_OFF_LINE, sw=1.1, rx=RX, dash="4 3")
    text(L + 26, 200, "Context", 17, "bold", fill=S_OFF_TEXT)
    state_label(L + sw - 26, 200, "not met", False)
    text(L + 26, 220, "≥ 2 unsafe across ≥ 2 batches", SMALL, fill=MUTED, maxw=sw - 52)
    text(L + 26, 239, "here: both flags in batch 1", SMALL, italic=True, fill=MUTED,
         maxw=sw - 52)
    rect(L + 28, 252, sw - 56, 78, fill=S_FILL, stroke=S_LINE, sw=2.2, rx=RX)
    text(L + 40, 275, "Batch", 17, "bold", fill=S_DARK)
    state_label(L + sw - 40, 275, "active", True)
    text(L + 40, 296, "≥ 1 unsafe in this batch", SMALL, fill=INK, maxw=sw - 80)
    text(L + 40, 317, "batch 1 only (2 unsafe)", SMALL, "bold", fill=S_DARK, maxw=sw - 80)

    # risk & decision = GroupStats + Policy.decide  (n_u, n_s: distinct audited origins)
    fx, fw = L + sw + 14, 222
    fl, fm = fx + 12, fw - 24
    text(fx, 94, "Risk & decision", SMALL, "bold", fill=MUTED, maxw=fw)
    rect(fx, 104, fw, 243, fill="#FFFFFF", stroke=S_LINE, sw=1.1, rx=RX)
    S_ = {"serif": True}
    SI = {"serif": True, "italic": True}
    SB = {"serif": True, "sub": True}
    rich(fl, 133, [("risk", SI), (" = (1+", S_), ("n", SI), ("u", SB), (") / (2+", S_),
                   ("n", SI), ("u", SB), ("+", S_), ("n", SI), ("s", SB), (")", S_)],
         size=19, maxw=fm)
    M_ = {"fill": MUTED}
    rich(fl, 155, [("n", {**SI, **M_}), ("u", {**SB, **M_}), (", ", M_),
                   ("n", {**SI, **M_}), ("s", {**SB, **M_}), (": unsafe / safe origins", M_)],
         size=16.5, maxw=fm)
    rich(fl, 183, [("pen", SI), (" = max(0, ", S_), ("risk", SI), (" − ½)", S_)],
         size=19, maxw=fm)
    rich(fl, 205, [("S:", {"weight": "bold", "fill": S_DARK}),
                   (" max over active scopes", {"fill": S_DARK})], size=SMALL, maxw=fm)
    line([(fl, 219), (fx + fw - 12, 219)], color=S_SEP, sw=1)
    rich(fl, 245, [("pen ≥ 0.25", {"weight": "bold"}), ("  →  ", {}),
                   ("withhold", {"weight": "bold", "fill": RED})], size=17, maxw=fm)
    rich(fl, 269, [("else rank by ", {}), ("cos − 0.5·pen", SI)], size=16.5, maxw=fm)
    line([(fl, 285), (fx + fw - 12, 285)], color=S_SEP, sw=1)
    text(fl, 310, "Batch 1: 2 unsafe, 0 safe", SMALL, "bold", fill=S_DARK, maxw=fm)
    text(fl, 331, "risk 3/4, pen 1/4 → withhold", SMALL, fill=S_DARK, maxw=fm)

    # localized example: R / C / M / S over A's two batches in context X
    tw = w - 32
    text(L, 378, "Localized example (A also has 2 flags in context Y)", SMALL, "bold",
         fill=MUTED, maxw=tw)
    cm, cs, cb = 78, 142, (tw - 78 - 142) / 2
    x_s, x_1, x_2 = L + cm, L + cm + cs, L + cm + cs + cb
    line([(L, 389), (L + tw, 389)], color=INK, sw=1.1)            # booktabs-style rules
    text(L + 10, 408, "Method", SMALL, "bold", fill=MUTED)
    text(x_s + 8, 408, "Deciding scope", SMALL, "bold", fill=MUTED, maxw=cs - 10)
    text(x_1 + 10, 408, "Batch 1 (ZX-91)", SMALL, "bold", fill=MUTED, maxw=cb - 12)
    text(x_2 + 10, 408, "Batch 2 (useful)", SMALL, "bold", fill=MUTED, maxw=cb - 12)
    line([(L, 418), (L + tw, 418)], color=INK, sw=0.8)
    rows = [
        ("R", "audited items only", ("leak", "leaks", RED), ("ok", "kept", INK, None)),
        ("C", "context · 1/4", ("x", "withheld", INK), ("x", "lost", RED, "lost")),
        ("M", "contributor · 1/3", ("x", "withheld", INK), ("x", "lost", RED, "lost")),
        ("S", "batch 1 only · 1/4", ("x", "withheld", INK), ("ok", "kept", S_DARK, "kept")),
    ]
    rh = 36
    for i, (m, scope, a, b) in enumerate(rows):
        y = 423 + (rh + 3) * i
        ours = m == "S"
        if ours:
            rect(L, y, tw, rh, fill=S_TINT, stroke=S_LINE, sw=1.6, rx=RX)
        elif i < 2:
            line([(L, y + rh + 1.5), (L + tw, y + rh + 1.5)], color="#E6E6E6", sw=1)
        kind2, s2, col2, emph = b
        if emph == "lost":
            rect(x_2 + 4, y + 5, cb - 8, rh - 10, fill=RED_F, stroke="none", rx=RX)
        elif emph == "kept":
            rect(x_2 + 4, y + 5, cb - 8, rh - 10, fill=S_FILL, stroke=S_LINE, sw=1.6, rx=RX)
        if ours:
            text(L + 10, y + 24, "S", 18, "bold", fill=S_DARK)
            text(L + 25, y + 24, "(ours)", SMALL, "bold", fill=S_DARK, maxw=cm - 27)
        else:
            text(L + 10, y + 24, m, 18, "bold")
        text(x_s + 8, y + 24, scope, SMALL, "bold" if ours else "normal",
             fill=S_DARK if ours else MUTED, maxw=cs - 10)
        kind1, s1, col1 = a
        {"x": badge_x, "ok": badge_ok, "leak": badge_leak}[kind1](x_1 + 20, y + rh / 2)
        text(x_1 + 34, y + 24, s1, 16.5, "normal", fill=col1, maxw=cb - 38)
        {"x": badge_x, "ok": badge_ok, "leak": badge_leak}[kind2](x_2 + 20, y + rh / 2)
        text(x_2 + 34, y + 24, s2, 17, "bold" if emph else "normal", fill=col2,
             maxw=cb - 38)
    end()


def panel_c():
    group("panel-c-retrieval")
    L = CX + 14
    RE = CX + CW - 14                                # right content edge
    title(L, 36, "(c) Governed retrieval & extensions", maxw=RE - L)

    qs = [("Q1", "What is the project code?"), ("Q2", "When is the Larkspur review?"),
          ("Q3", "Where should issues be escalated?")]
    for i, (q, s) in enumerate(qs):
        rich(L, 70 + 20 * i, [(q + "  ", {"weight": "bold"}), (s, {})], size=16.5,
             maxw=RE - L)

    bx, bw = L, 232
    mid = bx + bw / 2
    sx = bx + bw + 14
    sw_ = RE - sx
    sm = sw_ - 20
    Y0, SH, STRIDE = 134, 30, 38

    def sy(n):
        return Y0 + (n - 1) * STRIDE

    def step(n, label, kind):
        fill, stroke, swd, dash, ncol, tcol, wt = {
            "grey": (GREY_F, GREY, 1.0, None, GREY, INK, "normal"),
            "ours": (S_TINT, S_LINE, 1.1, None, S_LINE, S_DARK, "normal"),
            "core": (S_FILL, S_LINE, 2.2, None, S_DARK, S_DARK, "bold"),
            "amber": (AMBER_F, AMBER, 1.4, "5 3", AMBER_D, AMBER_D, "bold"),
        }[kind]
        y = sy(n)
        rect(bx, y, bw, SH, fill=fill, stroke=stroke, sw=swd, rx=RX, dash=dash)
        text(bx + 12, y + 20.5, str(n), 16.5, "bold", fill=ncol)
        text(bx + 30, y + 20.5, label, 17, wt, fill=tcol, maxw=bw - 38)
        if n < 7:
            main_arrow([(mid, y + SH), (mid, y + STRIDE - 1)])

    main_arrow([(mid, 118), (mid, Y0 - 1)])
    step(1, "Admission (λ ≥ u)", "grey")
    step(2, "Direct audit findings", "ours")
    step(3, "S: penalty / withhold", "core")
    step(4, "Re-rank & refill (4+4)", "ours")
    step(5, "Conflict check (flags only)", "grey")
    step(6, "S2-ID gate", "amber")
    step(7, "Answer model", "grey")

    # SL: content-lineage veto inside each candidate decision (LineagePolicy wraps decide)
    y3 = sy(3) + SH / 2
    ty = sy(3) - 14
    rect(sx, ty, sw_, 108, fill=TEAL_F, stroke=TEAL, sw=1.3, rx=RX)
    text(sx + 10, ty + 20, "SL · ours, optional", SMALL, "bold", fill=TEAL_D, maxw=sm)
    text(sx + 10, ty + 41, "vetoes a candidate at", SMALL, fill=INK, maxw=sm)
    text(sx + 10, ty + 60, "cos ≥ 0.8 to a claim of", SMALL, fill=INK, maxw=sm)
    text(sx + 10, ty + 79, "an unsafe-audited origin", SMALL, fill=INK, maxw=sm)
    text(sx + 10, ty + 99, "e.g. U’s relay (S: pen 0)", SMALL, italic=True, fill=TEAL_D,
         maxw=sm)
    line([(sx, y3), (bx + bw + 3, y3)], color=TEAL, sw=1.5, marker="a-teal")
    # the relay from panel (a) arrives along the bottom route
    rx_ = CX + CW + 1
    lineage_line([(AX + 6, ROUTE_Y), (rx_, ROUTE_Y), (rx_, ty + 54), (sx + sw_ + 3, ty + 54)])

    # S2-ID: MemLineage's sensitive-action gate on the final retrieved context
    y6 = sy(6) + SH / 2
    ay = sy(6) - 16
    rect(sx, ay, sw_, 108, fill=AMBER_F, stroke=AMBER, sw=1.3, rx=RX, dash="5 3")
    text(sx + 10, ay + 20, "S2-ID · hybrid, optional", SMALL, "bold", fill=AMBER_D, maxw=sm)
    text(sx + 10, ay + 41, "gate from MemLineage:", SMALL, fill=INK, maxw=sm)
    text(sx + 10, ay + 60, "sensitive query + non-", SMALL, fill=INK, maxw=sm)
    text(sx + 10, ay + 79, "principal memory in the", SMALL, fill=INK, maxw=sm)
    text(sx + 10, ay + 98, "final context → cleared", SMALL, "bold", fill=AMBER_D, maxw=sm)
    line([(sx, y6), (bx + bw + 3, y6)], color=AMBER, sw=1.5, dash="4 3", marker="a-amber")

    # illustrative outcomes of the running example
    oy = sy(7) + SH + 28
    text(L, oy, "Example outcomes", SMALL, "bold", fill=MUTED)
    outs = [(badge_x, "Q1", "ZX-91 withheld by S (step 3)"),
            (badge_ok, "Q2", "Larkspur note kept by S (pen 0)"),
            (badge_x, "Q3", "relay withheld by SL (step 3)")]
    for i, (g, q, s) in enumerate(outs):
        yy = oy + 22 + 21 * i
        g(L + 8, yy - 5.5, 7)
        rich(L + 22, yy, [(q + "  ", {"weight": "bold"}), (s, {})], size=SMALL,
             maxw=RE - L - 22)

    ny = oy + 22 + 21 * 3 + 12
    text(L, ny, "S2-ID is evaluated under Sybil and laundering attacks,", SMALL,
         italic=True, fill=MUTED, maxw=RE - L)
    text(L, ny + 19, "which move poison outside S’s audited scopes; its gate", SMALL,
         italic=True, fill=MUTED, maxw=RE - L)
    text(L, ny + 38, "uses no contributor identity.", SMALL, italic=True, fill=MUTED,
         maxw=RE - L)

    rich(L, 578, [("S", {"weight": "bold", "fill": S_DARK}), (": steps 1–5, 7    ", {"fill": MUTED}),
                  ("SL", {"weight": "bold", "fill": TEAL_D}), (": S + veto    ", {"fill": MUTED}),
                  ("S2-ID", {"weight": "bold", "fill": AMBER_D}), (": SL + step 6", {"fill": MUTED})],
         size=SMALL, maxw=RE - L)
    if ny + 38 > 560:
        WARN.append(f"panel (c) note reaches {ny + 38}")

    # evidence and policy from (b) into step 3
    ev_arrow([(BX + 16 + 284 + 14 + 222, y3), (bx - 3, y3)], color=S_LINE, marker="a-blue")
    end()


def legend():
    group("legend")
    y = 630
    x = 12
    items = [(GREY_F, GREY, None, "SAFE-Mem (unchanged)"),
             (S_FILL, S_LINE, None, "Ours: S + audit layer"),
             (TEAL_F, TEAL, None, "SL: our extension"),
             (AMBER_F, AMBER, "4 3", "S2-ID: hybrid (MemLineage gate)")]
    for f, s, d, label in items:
        rect(x, y - 12, 20, 14, fill=f, stroke=s, sw=1.2, rx=2, dash=d)
        x += 27
        x += text(x, y, label, SMALL) + 18
    line([(x, y - 15), (x, y + 3)], color=FAINT, sw=1)
    x += 14
    for g, label in ((badge_x, "unsafe / withheld"), (badge_open, "not audited"),
                     (badge_ok, "kept"), (badge_leak, "leaks")):
        g(x + 7, y - 5, 6.5)
        x += 19
        x += text(x, y, label, SMALL) + 14
    lineage_line([(x, y - 5), (x + 22, y - 5)], marker=None)
    x += 28
    x += text(x, y, "near-copy", SMALL)
    if x > W - 6:
        WARN.append(f"legend overflows: ends at {x:.0f} > {W - 6}")
    end()


def defs():
    def marker(mid, color, size=7):
        return (f'<marker id="{mid}" viewBox="0 0 10 10" refX="8.5" refY="5" '
                f'markerWidth="{size}" markerHeight="{size}" markerUnits="userSpaceOnUse" '
                f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>')

    return ("<defs>" + marker("a-main", "#4A4A4A", 8) + marker("a-ev", GREY)
            + marker("a-blue", S_LINE) + marker("a-teal", TEAL, 7)
            + marker("a-amber", AMBER, 7) + "</defs>")


def palette_comment():
    roles = [("text", INK), ("secondary text", MUTED), ("hairlines", FAINT),
             ("SAFE-Mem line", GREY), ("SAFE-Mem fill", GREY_F),
             ("S line / badges", S_LINE), ("S titles / text", S_DARK), ("S fill", S_FILL),
             ("S light fill", S_TINT), ("S panel background", S_BG), ("S separators", S_SEP),
             ("S inactive line", S_OFF_LINE), ("S inactive text", S_OFF_TEXT),
             ("S inactive fill (outer)", S_OFF_F1), ("S inactive fill (inner)", S_OFF_F2),
             ("SL line / near-copy connector", TEAL), ("SL text", TEAL_D), ("SL fill", TEAL_F),
             ("S2-ID line", AMBER), ("S2-ID text", AMBER_D), ("S2-ID fill", AMBER_F),
             ("unsafe / withheld", RED), ("unsafe fill", RED_F)]
    rows = "\n".join(f"  {hexv}  {name}" for name, hexv in roles)
    return ("<!-- PALETTE (find-and-replace a hex to recolour that role everywhere;\n"
            "     the generator make_figure.py defines the same constants)\n" + rows + "\n-->")


def build():
    panel_a()
    panel_b()
    panel_c()
    legend()
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="{W}" height="{H}">\n<title>Selective evidence propagation (S) on SAFE-Mem'
            f'</title>\n{palette_comment()}\n{defs()}\n'
            f'<rect x="0" y="0" width="{W}" height="{H}" fill="#FFFFFF"/>\n')
    return head + "\n".join(EL) + "\n</svg>\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    svg = build()
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    for wmsg in WARN:
        print("WARN", wmsg.encode("ascii", "replace").decode(), file=sys.stderr)
    print(f"wrote {a.out} ({len(svg)} bytes, {len(WARN)} warnings)")
