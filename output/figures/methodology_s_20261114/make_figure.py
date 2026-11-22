#!/usr/bin/env python3
"""Methodology figure: selective evidence propagation (S) on top of SAFE-Mem.

Writes an editable SVG (real text, no rasters). Dependency-free. Every mechanism,
threshold and step order is taken from the repository implementation. Notation follows
the methodology draft: support thresholds theta_bat, theta_ctx, delta_ctx, theta_src, delta_src
and the qualifying-context constants theta_Q, delta_Q (Eqs. 8-9); r, d, D (Eqs. 6-7);
withhold tau, rank weight lambda (Eqs. 10-11); SL threshold eta (Eq. 12); k claims + m chunks.
Their values in the main evaluated setting are stated in the caption (README.md). They are
constants in the code, not adapted at run time.

v3 (22 Nov 2026): panel (b) as three numbered steps (gates for ZX-91, risk -> decision, toy
R/C/M/S table); M chip "all", R chip "none", S2-ID box names MemLineage. Table outcomes are
checked by verify_toy_example.py. v2 (feedback "too dense with words"): visuals -- record tiles,
audit-ticket glyphs, the penalty bar chart against tau, scope chips, inline query outcomes and
a refill slot diagram. Earlier versions live in versions/ (see README.md).
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
    """parts: [(text, {'weight','fill','italic','serif','sub','sup'})] on one baseline."""
    small = lambda o: o.get("sub") or o.get("sup")  # noqa: E731
    total = sum(text_width(t, size * (SUB if small(o) else 1), o.get("weight") == "bold",
                           o.get("serif", False)) for t, o in parts)
    _check("".join(t for t, _ in parts), total, maxw, size)
    spans, shift = [], 0.0
    for t, o in parts:
        fam = SERIF if o.get("serif") else SANS
        it = ' font-style="italic"' if o.get("italic") else ""
        want = size * 0.22 if o.get("sub") else (-size * 0.36 if o.get("sup") else 0.0)
        dy, shift = want - shift, want
        extra = (f' dy="{dy:.1f}"' if dy else "") + (f' font-size="{size*SUB:.1f}"' if small(o) else "")
        spans.append(f'<tspan font-family="{fam}" font-weight="{o.get("weight", "normal")}" '
                     f'fill="{o.get("fill", INK)}"{it}{extra}>{esc(t)}</tspan>')
    EL.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" xml:space="preserve">'
              + "".join(spans) + "</text>")
    return total


MUT = {"fill": MUTED}


def sym(base, sub, fill=INK):
    """A threshold symbol such as theta_bat: serif italic base, upright serif subscript
    (the notation of the methodology draft, Eqs. 8-9)."""
    return [(base, {"serif": True, "italic": True, "fill": fill}),
            (sub, {"serif": True, "sub": True, "fill": fill})]


def nsup(sign, fill=INK):
    """n^- / n^+ (unsafe / safe root counts, Eq. 6): italic n, upright superscript sign."""
    return [("n", {"serif": True, "italic": True, "fill": fill}),
            (sign, {"serif": True, "sup": True, "fill": fill})]


MI = {"serif": True, "italic": True}  # a math symbol in running sans text


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


def badge_safe(cx, cy, r=7.5):
    """Audited SAFE (grey): distinct from 'kept' (lavender check, a retrieval outcome)."""
    EL.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{GREY}"/>')
    EL.append(f'<path d="M{cx-r*0.48},{cy+r*0.02} L{cx-r*0.12},{cy+r*0.38} L{cx+r*0.5},{cy-r*0.36}" '
              f'fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" '
              f'stroke-linejoin="round"/>')


GLYPH = {"x": badge_x, "ok": badge_ok, "o": badge_open, "leak": badge_leak, "safe": badge_safe}
TILE_H = 22


def tile(x, y, w, label, kind, fill=INK, weight="normal", bg="#FFFFFF", stroke="#C4C4C4",
         dash=None):
    """One stored memory as a small card: status glyph + short label."""
    rect(x, y, w, TILE_H, fill=bg, stroke=stroke, sw=1, rx=RX, dash=dash)
    if kind:
        GLYPH[kind](x + 11, y + TILE_H / 2, 6.5)
        text(x + 22, y + 16, label, SMALL, weight, fill=fill, maxw=w - 26)
    elif label:
        text(x + w / 2, y + 16, label, SMALL, weight, fill=fill, anchor="middle", maxw=w - 8)


def inline(x, y, items, size=SMALL, maxw=None):
    """Text and status glyphs on one baseline. items: (text, style) or ('@', kind)."""
    cx = x
    for t, o in items:
        if t == "@":
            GLYPH[o](cx + 7, y - 5.5, 6.5)
            cx += 16
        else:
            cx += rich(cx, y, [(t, o)] if isinstance(o, dict) else o, size=size)
    if maxw is not None and cx - x > maxw + 0.5:
        WARN.append(f"overflow {cx - x:.0f}>{maxw:.0f}: inline at ({x:.0f}, {y:.0f})")
    return cx - x


def ticket(x, y, kind, w=40, h=22):
    """An audit ticket: notched card with the verdict it returned."""
    rect(x, y, w, h, fill="#FFFFFF", stroke=GREY, sw=1.1, rx=RX)
    for nx in (x, x + w):
        EL.append(f'<circle cx="{nx}" cy="{y + h / 2}" r="4" fill="#FFFFFF" stroke="{GREY}" '
                  f'stroke-width="1.1"/>')
        EL.append(f'<rect x="{nx - (4.6 if nx == x else 0)}" y="{y + h / 2 - 5}" width="4.6" '
                  f'height="10" fill="#FFFFFF"/>')
    GLYPH[kind](x + w / 2, y + h / 2, 6.5)


def ledger_icon(x, y):
    """A journal: page with ruled lines (append-only ledger)."""
    rect(x, y, 22, 28, fill="#FFFFFF", stroke=GREY, sw=1.1, rx=2)
    for i in range(4):
        line([(x + 5, y + 7 + 5 * i), (x + 17, y + 7 + 5 * i)], color=GREY, sw=1.1)


def chip(x, y, w, parts, bg, stroke, h=22, size=SMALL):
    """A small rounded label (scope chip); parts as for rich()."""
    rect(x, y, w, h, fill=bg, stroke=stroke, sw=1, rx=RX)
    tw_ = sum(text_width(t, size * (SUB if o.get("sub") else 1), o.get("weight") == "bold",
                         o.get("serif", False)) for t, o in parts)
    rich(x + (w - tw_) / 2, y + 16, parts, size=size, maxw=w - 6)


def panel_a():
    group("panel-a")
    L, R = AX + 14, AX + AW - 14
    w = R - L
    title(L, 36, "(a) Provenance & audits", maxw=w)

    # contributor A: context X (localized placement: seeds and planted claim share batch 1)
    text(L, 64, "Contributor A", 17, "bold", maxw=w)
    rect(L, 72, w, 134, fill="#FAFAFA", stroke="#C4C4C4", sw=1, rx=RX)
    text(L + 8, 89, "context X", SMALL, "bold", fill=MUTED)
    b1w = 158
    rect(L + 8, 96, b1w, 102, fill="#FFFFFF", stroke="#D6D6D6", sw=1, rx=RX)
    text(L + 16, 112, "batch 1", SMALL, fill=MUTED)
    tile(L + 14, 118, b1w - 12, "payee: QX Ltd", "x")
    tile(L + 14, 143, b1w - 12, "escalate: ops@", "x")
    tile(L + 14, 168, b1w - 12, "code: ZX-91", "o", fill=RED, weight="bold")
    b2x = L + 8 + b1w + 8
    rect(b2x, 96, R - 8 - b2x, 102, fill="#FFFFFF", stroke="#D6D6D6", sw=1, rx=RX)
    text(b2x + 8, 112, "batch 2", SMALL, fill=MUTED)
    tile(b2x + 6, 118, R - 8 - b2x - 12, "Larkspur", "o", fill=S_DARK, weight="bold")

    # context Y, collapsed: A's other two audited seeds (both in batch 1)
    rect(L, 214, w, 34, fill="#FAFAFA", stroke="#C4C4C4", sw=1, rx=RX)
    text(L + 8, 236, "context Y", SMALL, "bold", fill=MUTED)
    inline(L + 104, 236, [("b1 ", MUT), ("@", "x"), ("@", "x"), ("     b2 ", MUT),
                          ("@", "o"), ("@", "o")])

    # contributor B: one benign item, audited safe
    text(L, 276, "Contributor B", 17, "bold", maxw=w)
    tile(L + 150, 260, w - 150, "benign", "safe", fill=MUTED)

    # unrelated contributor U: an unaudited near-copy of an unsafe-AUDITED seed
    text(L, 308, "Contributor U", 17, "bold", maxw=w)
    tile(L + 150, 292, w - 150, "escalate: ops@", "o", fill=RED, weight="bold")
    text(R, 336, "near-copy; no audits", SMALL, italic=True, fill=TEAL_D, anchor="end")
    jx = AX + 6                                    # connector spine, left margin
    EL.append(f'<circle cx="{jx}" cy="320" r="2.6" fill="{TEAL}"/>')
    lineage_line([(jx, 303), (jx, 320), (L + 140, 320), (L + 140, 303), (L + 148, 303)],
                 marker=None)
    lineage_line([(jx, 320), (jx, 154), (L + 12, 154)])                # relay -> audited seed
    lineage_line([(jx, 320), (jx, ROUTE_Y)], marker=None)              # relay -> SL, panel (c)

    # audit allocation (oracle; identical ticket IDs for R, C, M, S)
    rich(L, 404, [("5 audit tickets", {"weight": "bold"}),
                  ("  same for R, C, M, S", {"fill": MUTED})], size=17, maxw=w)
    for i, kind in enumerate(("x", "x", "x", "x", "safe")):
        ticket(L + 6 + 50 * i + (12 if i == 4 else 0), 416, kind)
    text(L + 6 + 95, 462, "A’s seeds", SMALL, fill=MUTED, anchor="middle")
    text(L + 6 + 212 + 20, 462, "B", SMALL, fill=MUTED, anchor="middle")
    line([(L + 6, 447), (L + 196, 447)], color=FAINT, sw=1)

    rect(L, 510, w, 50, fill=GREY_F, stroke=GREY, sw=1, rx=RX)
    ledger_icon(L + 10, 521)
    text(L + 42, 531, "Evidence ledger", 17, "bold")
    text(L + 42, 551, "one vote per root", SMALL, fill=MUTED, maxw=w - 54)
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

    # (1) support gates = ledger.active_scopes (draft Eqs. 8-9), checked for record ZX-91
    # (contributor A, context X, batch 1). x = an unsafe-audited root of A. The qualifying
    # rule has its own constants (theta_Q, delta_Q), not the context gate's.
    tw = w - 32
    IT = {"italic": True, "fill": MUTED}
    rich(L, 94, [("1  Support gates for ", {"weight": "bold", "fill": MUTED}),
                 ("code: ZX-91", {"weight": "bold", "fill": RED}),
                 ("  (A · context X · batch 1)", {"fill": MUTED})], size=SMALL, maxw=tw)
    c_cond, c_here = L + 108, L + 326
    gates = [
        ("Batch", True, [("≥ ", {}), *sym("θ", "bat"), (" ", {}), ("@", "x"), (" in its batch", {})],
         [("b1 ", {}), ("@", "x"), ("@", "x")], "active"),
        ("Context", False, [("≥ ", MUT), *sym("θ", "ctx", MUTED), (" ", MUT), ("@", "x"),
                            (" in ≥ ", MUT), *sym("δ", "ctx", MUTED), (" batches", MUT)],
         [("b1 ", IT), ("@", "x"), ("@", "x"), ("  b2 ", IT), ("@", "o")], "not met"),
        ("Contributor", False, [("≥ ", MUT), *sym("θ", "src", MUTED), (" ", MUT), ("@", "x"),
                                (", ≥ ", MUT), *sym("δ", "src", MUTED), (" qualifying*", MUT)],
         [("4 ", IT), ("@", "x"), (", 0 qualifying", IT)], "not met"),
    ]
    for i, (nm, on, cond, here, state) in enumerate(gates):
        y = 104 + 31 * i
        rect(L, y, tw, 27, fill=S_FILL if on else S_OFF_F1, stroke=S_LINE if on else S_OFF_LINE,
             sw=1.8 if on else 1.0, rx=RX, dash=None if on else "4 3")
        text(L + 10, y + 19, nm, SMALL, "bold", fill=S_DARK if on else S_OFF_TEXT)
        inline(c_cond, y + 19, cond, maxw=c_here - c_cond - 8)
        inline(c_here, y + 19, here, maxw=L + tw - 66 - c_here)
        state_label(L + tw - 10, y + 19, state, on)
    inline(L, 212, [("* qualifying context: ≥ ", IT), *[(t, {**o, "fill": MUTED}) for t, o in sym("θ", "Q")],
                    (" ", IT), ("@", "x"), (" in ≥ ", IT), *[(t, {**o, "fill": MUTED}) for t, o in sym("δ", "Q")],
                    (" batches", IT)], maxw=tw)

    # (2) risk & decision = GroupStats + Policy.decide; bars = d for n+ = 0
    S_ = {"serif": True}
    SI = {"serif": True, "italic": True}
    DK = {"fill": S_DARK}
    text(L, 240, "2  Risk → decision", SMALL, "bold", fill=MUTED)
    lw = 250
    g = 64  # gloss column
    for y_, gl, parts in (
        (266, "risk", [("r", SI), (" = (1+", S_), *nsup("−"), (")/(2+", S_), *nsup("−"), ("+", S_),
                       *nsup("+"), (")", S_)]),
        (290, "penalty", [("d", SI), (" = max(0, ", S_), ("r", SI), (" − ½)", S_)]),
        (314, "S uses", [("D", {**SI, **DK}), (" = max of active ", DK), ("d", {**SI, **DK})]),
    ):
        text(L, y_, gl, SMALL, italic=True, fill=MUTED)
        rich(L + g, y_, parts, size=SMALL if gl == "S uses" else 18, maxw=lw - g)
    rect(L, 330, 12, 12, fill=RED, stroke="none", rx=1)
    rich(L + 18, 341, [("D", SI), (" ≥ ", {}), ("τ", SI), (" → ", {}),
                       ("withhold", {"weight": "bold", "fill": RED})], size=SMALL, maxw=lw - 18)
    rect(L, 350, 12, 12, fill=S_LINE, stroke="none", rx=1)
    rich(L + 18, 361, [("else rank by ", {}), ("s − λD", SI), ("  (", MUT), ("s", {**SI, **MUT}),
                       (": similarity)", MUT)], size=SMALL, maxw=lw - 18)
    # chart
    x0 = L + lw + 16
    ax0, base, scale, slot = x0 + 24, 334, 240.0, 56
    tau_y = base - 0.25 * scale
    line([(ax0, 252), (ax0, base), (L + tw - 4, base)], color=MUTED, sw=1)
    rich(ax0 - 16, 312, [("d", {**SI, "fill": MUTED})], size=17)
    for i, (num, den) in enumerate(((0, 1), (1, 6), (1, 4))):
        h = scale * num / den
        bx_ = ax0 + 16 + slot * i
        withhold = num * 4 >= den        # d >= tau (inclusive), exact
        if h:
            rect(bx_, base - h, 30, h, fill=RED if withhold else S_LINE, stroke="none", rx=1)
        else:
            line([(bx_, base - 1), (bx_ + 30, base - 1)], color=S_LINE, sw=2.2)
        rich(bx_ + 15 - 4, base + 17, [(str(i), S_)], size=16)
    rich(ax0 + 4, base + 35, [("unsafe roots ", MUT), *nsup("−", MUTED), ("  (with ", MUT),
                              *nsup("+", MUTED), (" = 0)", MUT)], size=SMALL, maxw=L + tw - ax0 - 8)
    line([(ax0, tau_y), (L + tw - 4, tau_y)], color=RED, sw=1.2, dash="4 3")
    rich(ax0 - 16, tau_y + 5, [("τ", {**SI, "fill": RED})], size=18)
    # worked example: batch 1 has n- = 2, n+ = 0 -> r = 3/4, d = 1/4 = tau -> withheld (>=)
    rich(ax0 + 6, 258, [("ZX-91: ", {"weight": "bold", "fill": S_DARK}), ("r", {**SI, **DK}),
                        (" = 3/4, ", DK), ("d", {**SI, **DK}), (" = 1/4 = ", DK), ("τ", {**SI, **DK})],
         size=SMALL, maxw=L + tw - ax0 - 8)
    line([(ax0 + 16 + slot * 2 + 15, 263), (ax0 + 16 + slot * 2 + 15, tau_y - 2)], color=S_DARK, sw=1)
    line([(x0 - 8, 252), (x0 - 8, 364)], color=S_SEP, sw=1)

    # (3) toy example: R / C / M / S on A's two context-X records. Outcomes reproduced by
    # running the frozen Policy.decide on this toy ledger (README "Verification").
    T0 = 392
    rich(L, T0, [("3  Toy example: A’s context-X records", {"weight": "bold", "fill": MUTED})],
         size=SMALL, maxw=tw)
    cm, cs, cb = 78, 142, (tw - 78 - 142) / 2
    x_s, x_1, x_2 = L + cm, L + cm + cs, L + cm + cs + cb
    line([(L, T0 + 9), (L + tw, T0 + 9)], color=INK, sw=1.1)            # booktabs-style rules
    text(L + 10, T0 + 30, "Method", SMALL, "bold", fill=MUTED)
    rich(x_s + 8, T0 + 30, [("scope · ", {"weight": "bold", "fill": MUTED}),
                            ("D", {**SI, "fill": MUTED})], size=SMALL, maxw=cs - 10)
    tile(x_1 + 8, T0 + 13, cb - 20, "code: ZX-91", "o", fill=RED, weight="bold")
    tile(x_2 + 8, T0 + 13, cb - 20, "Larkspur", "o", fill=S_DARK, weight="bold")
    line([(L, T0 + 40), (L + tw, T0 + 40)], color=INK, sw=0.8)
    rows = [
        ("R", "none", None, ("leak", "leaks", RED), ("ok", "kept", INK, None)),
        ("C", "ctx", "1/4", ("x", "withheld", INK), ("x", "lost", RED, "lost")),
        ("M", "all", "1/3", ("x", "withheld", INK), ("x", "lost", RED, "lost")),
        ("S", "bat", "1/4", ("x", "withheld", INK), ("ok", "kept", S_DARK, "kept")),
    ]
    rh = 32
    for i, (m, scope, val, a, b) in enumerate(rows):
        y = T0 + 45 + (rh + 3) * i
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
            text(L + 10, y + 22, "S", 18, "bold", fill=S_DARK)
            text(L + 25, y + 22, "(ours)", SMALL, "bold", fill=S_DARK, maxw=cm - 27)
        else:
            text(L + 10, y + 22, m, 18, "bold")
        parts = [(scope, {"weight": "bold" if ours else "normal",
                          "fill": S_DARK if ours else MUTED})]
        if val:
            parts.append((" · " + val, {"weight": "bold" if ours else "normal",
                                        "fill": S_DARK if ours else MUTED}))
        chip(x_s + 8, y + 5, 92, parts, S_FILL if ours else "#F4F4F4",
             S_LINE if ours else "#D6D6D6")
        kind1, s1, col1 = a
        GLYPH[kind1](x_1 + 20, y + rh / 2)
        text(x_1 + 34, y + 22, s1, 16.5, "normal", fill=col1, maxw=cb - 38)
        GLYPH[kind2](x_2 + 20, y + rh / 2)
        text(x_2 + 34, y + 22, s2, 17, "bold" if emph else "normal", fill=col2,
             maxw=cb - 38)
    end()


def panel_c():
    group("panel-c-retrieval")
    L = CX + 14
    RE = CX + CW - 14                                # right content edge
    title(L, 36, "(c) Governed retrieval & extensions", maxw=RE - L)

    # the three example queries, each with its outcome (illustration, not results)
    qs = [("Q1", "project code?", "x", "ZX-91", "S", S_DARK),
          ("Q2", "Larkspur review day?", "ok", "Larkspur", "S", S_DARK),
          ("Q3", "where to escalate?", "x", "relay", "SL", TEAL_D)]
    ox = L + 236
    for i, (q, s, g, mem, by, col) in enumerate(qs):
        y = 70 + 21 * i
        rich(L, y, [(q + "  ", {"weight": "bold"}), (s, {})], size=16.5, maxw=ox - L - 8)
        inline(ox, y, [("@", g), (" " + mem + "  ", {"fill": INK}),
                       (by, {"weight": "bold", "fill": col})], maxw=RE - ox)

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
        if isinstance(label, str):
            text(bx + 30, y + 20.5, label, 17, wt, fill=tcol, maxw=bw - 38)
        else:  # (text, is_math) parts: math in serif italic, as in the draft's equations
            rich(bx + 30, y + 20.5, [(t, {"weight": wt, "fill": tcol, **(MI if m else {})})
                                     for t, m in label], size=17, maxw=bw - 38)
        if n < 7:
            main_arrow([(mid, y + SH), (mid, y + STRIDE - 1)])

    main_arrow([(mid, 118), (mid, Y0 - 1)])
    step(1, [("Admission ", False), ("α", True), ("(", False), ("x", True), (", ", False),
             ("q", True), (")", False)], "grey")                     # draft Eq. 2
    step(2, "Direct audit findings", "ours")
    step(3, "S: penalty / withhold", "core")
    step(4, [("Re-rank & refill (", False), ("k", True), (" + ", False), ("m", True),
             (")", False)], "ours")                                  # k claims + m chunks
    step(5, "Conflict check (flags only)", "grey")
    step(6, "S2-ID gate", "amber")
    step(7, "Answer model", "grey")

    # SL: content-lineage veto inside each candidate decision (LineagePolicy wraps decide)
    y3 = sy(3) + SH / 2
    ty = sy(3) - 14
    rect(sx, ty, sw_, 108, fill=TEAL_F, stroke=TEAL, sw=1.3, rx=RX)
    text(sx + 10, ty + 20, "SL · ours, exploratory", SMALL, "bold", fill=TEAL_D, maxw=sm)
    tw_ = 84
    tile(sx + 8, ty + 32, tw_, "relay", "o", fill=RED, weight="bold")
    tile(sx + sw_ - 8 - tw_, ty + 32, tw_, "seed", "x", fill=INK)
    lineage_line([(sx + 8 + tw_ + 2, ty + 43), (sx + sw_ - 8 - tw_ - 4, ty + 43)])
    rich(sx + sw_ / 2 - 27, ty + 74, [("cos ≥ ", {}), ("η", MI)], size=SMALL)
    rich(sx + 10, ty + 99, [("→ relay vetoed (S: ", {"italic": True, "fill": TEAL_D}),
                            ("D", {**MI, "fill": TEAL_D}),
                            (" = 0)", {"italic": True, "fill": TEAL_D})], size=SMALL, maxw=sm)
    line([(sx, y3), (bx + bw + 3, y3)], color=TEAL, sw=1.5, marker="a-teal")
    # the relay from panel (a) arrives along the bottom route
    rx_ = CX + CW + 1
    lineage_line([(AX + 6, ROUTE_Y), (rx_, ROUTE_Y), (rx_, ty + 43), (sx + sw_ + 3, ty + 43)])

    # S2-ID: MemLineage's sensitive-action gate on the final retrieved context
    y6 = sy(6) + SH / 2
    ay = sy(6) - 16
    rect(sx, ay, sw_, 108, fill=AMBER_F, stroke=AMBER, sw=1.3, rx=RX, dash="5 3")
    text(sx + 10, ay + 20, "S2-ID: MemLineage gate", SMALL, "bold", fill=AMBER_D, maxw=sm)
    text(sx + 10, ay + 43, "sensitive query, and", SMALL, fill=INK, maxw=sm)
    text(sx + 10, ay + 63, "any non-principal memory", SMALL, fill=INK, maxw=sm)
    text(sx + 10, ay + 92, "→ context", SMALL, "bold", fill=AMBER_D)
    rect(sx + 96, ay + 76, 62, TILE_H, fill="#FFFFFF", stroke=AMBER, sw=1.2, rx=RX, dash="3 2")
    rich(sx + 120, ay + 93, [("∅", {"serif": True, "fill": AMBER_D})], size=18)
    line([(sx, y6), (bx + bw + 3, y6)], color=AMBER, sw=1.5, dash="4 3", marker="a-amber")

    # re-rank & refill, drawn for Q1: claims served (top k); R serves ZX-91, S refills
    oy = sy(7) + SH + 44
    rich(L, oy, [("Q1: served claims (top ", {"weight": "bold", "fill": MUTED}),
                 ("k", {**MI, "fill": MUTED}), (")", {"weight": "bold", "fill": MUTED})],
         size=SMALL)
    tw2, gap = 74, 5
    for r_, (m, col) in enumerate((("R", INK), ("S", S_DARK))):
        yy = oy + 12 + 32 * r_
        text(L, yy + 16, m, 18, "bold", fill=col)
        for j in range(4):
            xx = L + 26 + (tw2 + gap) * j
            if r_ == 0 and j == 0:
                tile(xx, yy, tw2, "ZX-91", "leak", fill=RED, weight="bold")
            elif r_ == 1 and j == 3:
                tile(xx, yy, tw2, "refill", None, fill=S_DARK, bg=S_TINT, stroke=S_LINE,
                     dash="3 2")
            else:
                tile(xx, yy, tw2, "", None, bg=GREY_F, stroke="#D6D6D6")
    xw = L + 26 + (tw2 + gap) * 4 + 8
    tile(xw, oy + 44, RE - xw, "ZX-91", "x", fill=MUTED)

    rich(L, 578, [("S", {"weight": "bold", "fill": S_DARK}), (": steps 1–5, 7    ", {"fill": MUTED}),
                  ("SL", {"weight": "bold", "fill": TEAL_D}), (": S + veto    ", {"fill": MUTED}),
                  ("S2-ID", {"weight": "bold", "fill": AMBER_D}), (": SL + step 6", {"fill": MUTED})],
         size=SMALL, maxw=RE - L)

    # evidence and policy from (b) into step 3
    ev_arrow([(BX + BW, y3), (bx - 3, y3)], color=S_LINE, marker="a-blue")
    end()


def legend():
    group("legend")
    y = 630
    x = 12
    items = [(GREY_F, GREY, None, "SAFE-Mem (unchanged)"),
             (S_FILL, S_LINE, None, "S (ours)"),
             (TEAL_F, TEAL, None, "SL (exploratory)"),
             (AMBER_F, AMBER, "4 3", "S2-ID (exploratory)")]
    for f, s, d, label in items:
        rect(x, y - 12, 20, 14, fill=f, stroke=s, sw=1.2, rx=2, dash=d)
        x += 27
        x += text(x, y, label, SMALL) + 16
    line([(x, y - 15), (x, y + 3)], color=FAINT, sw=1)
    x += 12
    for g, label in ((badge_x, "unsafe / withheld"), (badge_safe, "audited safe"),
                     (badge_open, "unaudited"), (badge_ok, "kept"), (badge_leak, "leaks")):
        g(x + 7, y - 5, 6.5)
        x += 19
        x += text(x, y, label, SMALL) + 12
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
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(svg)
    for wmsg in WARN:
        print("WARN", wmsg.encode("ascii", "replace").decode(), file=sys.stderr)
    print(f"wrote {a.out} ({len(svg)} bytes, {len(WARN)} warnings)")
