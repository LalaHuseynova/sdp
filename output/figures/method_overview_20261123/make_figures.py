#!/usr/bin/env python3
"""Figure A (method overview) and Figure B (worked example) for the S paper.

Dependency-free; writes editable SVG with live text. Both figures share one style module
(palette, type scale, glyphs, box and arrow styles). Visual language adapted from the
reference paper (numbered stage headers, few rounded boxes, thick stage arrows, one accent
colour for the proposed component). Every mechanism shown is taken from the frozen code:
  provenance, audits, one vote per root ..... src/ams/research/dynamic/models.py, ledger.py
  scopes, gates, r, d ...................... ledger.py (GroupStats, active_scopes)
  D, withhold / re-rank, R/C/M/S ........... src/ams/research/dynamic/policies.py (Policy.decide)
  admission, refill to k + m, conflicts .... src/ams/research/retrieval/adapter.py
Figure B's outcomes are the frozen Policy.decide on the toy ledger
(../methodology_s_20261114/verify_toy_example.py).

    python make_figures.py            # writes fig_A_overview.svg and fig_B_example.svg

Canvas width 1390 units = 6.75 in (ICML full width); 1 pt = 2.86 units. Smallest text 16 units.
"""

import sys

W = 1390
SANS = "Arial, Helvetica, sans-serif"
SERIF = "'Times New Roman', Times, serif"
MIN_TEXT = 16

# ---- PALETTE (same roles and hex values as the earlier method figure) --------------------
INK, MUTED, FAINT = "#1E1E1E", "#5A5A5A", "#CFCFCF"
GREY, GREY_F, GREY_L = "#7A7A7A", "#F2F2F2", "#9A9A9A"       # SAFE-Mem (unchanged)
S_LINE, S_DARK = "#7461B8", "#4B3C8C"                          # S (ours)
S_FILL, S_TINT = "#ECE8F8", "#F6F4FC"
S_OFF_LINE, S_OFF_TEXT = "#ADA3D1", "#76699F"                  # S: scope not supported
RED, RED_F = "#B8322A", "#F8E3E1"                              # unsafe / withheld / lost
TEAL, TEAL_D, TEAL_F = "#2B7F73", "#1E5E55", "#E4F2EF"         # SL (exploratory)
AMBER, AMBER_D, AMBER_F = "#C77700", "#8A5300", "#FDF1DD"      # S2-ID (exploratory hybrid)
ARROW = "#3A3A3A"

_AW = {
    " ": 278, "!": 278, "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333, ".": 278,
    "/": 278, ":": 278, ";": 278, "=": 584, "?": 556, "@": 1015, "&": 667, "'": 191,
    "’": 222, "“": 333, "”": 333, "·": 278, "≥": 549, "≤": 549, "<": 584, "−": 584,
    "→": 1000, "½": 834, "λ": 500, "τ": 500, "|": 260, "∅": 713, "Γ": 578,
    "I": 278, "J": 500, "L": 556, "M": 833, "W": 944, "F": 611, "T": 611, "Z": 611,
    "C": 722, "D": 722, "H": 722, "N": 722, "R": 722, "U": 722, "G": 778, "O": 778, "Q": 778,
    "f": 278, "i": 222, "j": 222, "l": 222, "t": 278, "r": 333, "m": 833, "w": 722,
    "c": 500, "k": 500, "s": 500, "v": 500, "x": 500, "y": 500, "z": 500,
}
_BOLD = {"b": 611, "d": 611, "g": 611, "h": 611, "n": 611, "o": 611, "p": 611, "q": 611,
         "u": 611, "r": 389, "t": 333, "f": 333, "i": 278, "l": 278, "c": 556, "k": 556,
         "s": 556, "v": 556, "y": 556, "x": 556, "z": 500, "m": 889, "w": 778}
SUB = 0.75


def text_width(s, size, bold=False, serif=False):
    total = 0
    for ch in s:
        w = (_BOLD.get(ch) if bold else None) or _AW.get(ch, 556)
        if bold and ch.isupper():
            w *= 1.06
        total += w
    return total / 1000 * size * (0.9 if serif else 1.0)


class Fig:
    """One SVG canvas: element list + layout warnings."""

    def __init__(self, name, h):
        self.name, self.h, self.el, self.warn = name, h, [], []

    # -- primitives ----------------------------------------------------------------------
    def _chk(self, s, w, maxw, size):
        if maxw is not None and w > maxw + 0.5:
            self.warn.append(f"overflow {w:.0f}>{maxw:.0f}: {s!r}")
        if size < MIN_TEXT:
            self.warn.append(f"text below {MIN_TEXT}u: {s!r}")

    def text(self, x, y, s, size=18, weight="normal", fill=INK, anchor="start", italic=False,
             serif=False, maxw=None):
        w = text_width(s, size, weight == "bold", serif)
        self._chk(s, w, maxw, size)
        it = ' font-style="italic"' if italic else ""
        self.el.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{SERIF if serif else SANS}" '
                       f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
                       f'text-anchor="{anchor}"{it}>{esc(s)}</text>')
        return w

    def rich(self, x, y, parts, size=18, maxw=None, anchor="start"):
        """parts: [(text, {'weight','fill','italic','serif','sub','sup'})] on one baseline."""
        small = lambda o: o.get("sub") or o.get("sup")  # noqa: E731
        total = sum(text_width(t, size * (SUB if small(o) else 1), o.get("weight") == "bold",
                               o.get("serif", False)) for t, o in parts)
        self._chk("".join(t for t, _ in parts), total, maxw, size)
        if anchor == "middle":
            x -= total / 2
        elif anchor == "end":
            x -= total
        spans, shift = [], 0.0
        for t, o in parts:
            want = size * 0.22 if o.get("sub") else (-size * 0.38 if o.get("sup") else 0.0)
            dy, shift = want - shift, want
            extra = (f' dy="{dy:.1f}"' if dy else "") + \
                    (f' font-size="{size * SUB:.1f}"' if small(o) else "")
            it = ' font-style="italic"' if o.get("italic") else ""
            spans.append(f'<tspan font-family="{SERIF if o.get("serif") else SANS}" '
                         f'font-weight="{o.get("weight", "normal")}" '
                         f'fill="{o.get("fill", INK)}"{it}{extra}>{esc(t)}</tspan>')
        self.el.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" xml:space="preserve">'
                       + "".join(spans) + "</text>")
        return total

    def rect(self, x, y, w, h, fill="none", stroke=FAINT, sw=1.2, rx=6, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.el.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                       f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, pts, color=GREY, sw=1.4, dash=None, marker=None):
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = f' marker-end="url(#{marker})"' if marker else ""
        self.el.append(f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{sw}" '
                       f'stroke-linejoin="round" stroke-linecap="round"{d}{m}/>')

    def raw(self, s):
        self.el.append(s)

    def group(self, gid):
        self.el.append(f'<g id="{gid}">')

    def end(self):
        self.el.append("</g>")

    # -- shared components ---------------------------------------------------------------
    def stage_arrow(self, x0, x1, y, color=ARROW):
        """Thick arrow between stages / columns."""
        self.line([(x0, y), (x1 - 2, y)], color=color, sw=3.2, marker="a-big" if color == ARROW
                  else "a-big-s")

    def flow(self, x0, y0, x1, y1, color=ARROW, sw=2):
        self.line([(x0, y0), (x1, y1)], color=color, sw=sw,
                  marker={ARROW: "a-small", S_LINE: "a-small-s"}.get(color, "a-small-g"))

    def header(self, x, y, n, label, color=INK, maxw=None):
        """Numbered stage header, as in the reference paper ("1. Attacker input")."""
        self.raw(f'<circle cx="{x + 12}" cy="{y - 7.5}" r="12.5" fill="{color}"/>')
        self.raw(f'<text x="{x + 12}" y="{y - 1.2}" font-family="{SANS}" font-size="17" '
                 f'font-weight="bold" fill="#fff" text-anchor="middle">{n}</text>')
        self.text(x + 32, y, label, 22, "bold", fill=color, maxw=maxw)

    def stage(self, x, y, w, h, ours=False):
        if ours:
            self.rect(x, y, w, h, fill=S_TINT, stroke=S_LINE, sw=2.6, rx=14)
        else:
            self.rect(x, y, w, h, fill="#FFFFFF", stroke=GREY_L, sw=1.6, rx=14)

    def pill(self, x, y, w, h, kind="grey", dash=None):
        fill, stroke, sw = {"grey": (GREY_F, GREY_L, 1.3), "ours": (S_FILL, S_LINE, 1.8),
                            "light": ("#FFFFFF", S_LINE, 1.4), "off": ("#FFFFFF", S_OFF_LINE, 1.1),
                            "red": (RED_F, RED, 1.4), "white": ("#FFFFFF", GREY_L, 1.2),
                            "teal": (TEAL_F, TEAL, 1.6), "amber": (AMBER_F, AMBER, 1.6)}[kind]
        self.rect(x, y, w, h, fill=fill, stroke=stroke, sw=sw, rx=min(h / 2, 10), dash=dash)

    # glyphs (same semantics as the earlier figure)
    def g_x(self, cx, cy, r=8):        # audited UNSAFE / withheld / lost
        self.raw(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{RED}"/>')
        k = r * 0.45
        self.raw(f'<path d="M{cx-k:.1f},{cy-k:.1f} L{cx+k:.1f},{cy+k:.1f} M{cx+k:.1f},{cy-k:.1f} '
                 f'L{cx-k:.1f},{cy+k:.1f}" stroke="#fff" stroke-width="2" stroke-linecap="round"/>')

    def _check(self, cx, cy, r, color):
        self.raw(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{color}"/>')
        self.raw(f'<path d="M{cx-r*0.48:.1f},{cy+r*0.02:.1f} L{cx-r*0.12:.1f},{cy+r*0.38:.1f} '
                 f'L{cx+r*0.5:.1f},{cy-r*0.36:.1f}" fill="none" stroke="#fff" stroke-width="2" '
                 f'stroke-linecap="round" stroke-linejoin="round"/>')

    def g_ok(self, cx, cy, r=8):       # kept / served / scope supported
        self._check(cx, cy, r, S_LINE)

    def g_safe(self, cx, cy, r=8):     # audited SAFE
        self._check(cx, cy, r, GREY)

    def g_open(self, cx, cy, r=8):     # unaudited
        self.raw(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r - 0.8}" fill="#fff" stroke="#8A8A8A" '
                 f'stroke-width="1.6"/>')

    def g_leak(self, cx, cy, r=8):     # served although planted
        self.raw(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r - 0.8}" fill="#fff" stroke="{RED}" '
                 f'stroke-width="2"/>')
        self.raw(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r * 0.33:.1f}" fill="{RED}"/>')

    def g_off(self, cx, cy, r=8):      # scope not supported
        self.raw(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r - 0.8}" fill="#fff" '
                 f'stroke="{S_OFF_LINE}" stroke-width="1.6"/>')
        self.raw(f'<path d="M{cx-r*0.4:.1f},{cy:.1f} L{cx+r*0.4:.1f},{cy:.1f}" '
                 f'stroke="{S_OFF_LINE}" stroke-width="1.8" stroke-linecap="round"/>')

    def glyph(self, kind, cx, cy, r=8):
        {"x": self.g_x, "ok": self.g_ok, "safe": self.g_safe, "o": self.g_open,
         "leak": self.g_leak, "off": self.g_off}[kind](cx, cy, r)

    def inline(self, x, y, items, size=18, maxw=None, anchor="start"):
        """Text and glyphs on one baseline: items are (text, style) or ('@', kind)."""
        if anchor == "middle":
            x -= sum(18 if t == "@" else text_width(t, size, o.get("weight") == "bold",
                                                     o.get("serif", False)) for t, o in items) / 2
        cx = x
        for t, o in items:
            if t == "@":
                self.glyph(o, cx + 8, y - 6, 7.5)
                cx += 18
            else:
                cx += self.rich(cx, y, [(t, o)], size=size)
        if maxw is not None and cx - x > maxw + 0.5:
            self.warn.append(f"overflow {cx - x:.0f}>{maxw:.0f}: inline at ({x:.0f}, {y:.0f})")
        return cx - x

    # icons
    def ticket(self, x, y, w=38, h=22, verdict=None):
        self.rect(x, y, w, h, fill="#FFFFFF", stroke=GREY, sw=1.2, rx=3)
        for nx in (x, x + w):
            self.raw(f'<circle cx="{nx}" cy="{y + h / 2}" r="4" fill="#FFFFFF" stroke="{GREY}" '
                     f'stroke-width="1.2"/>')
            self.raw(f'<rect x="{nx - (4.7 if nx == x else 0)}" y="{y + h / 2 - 5.2}" width="4.7" '
                     f'height="10.4" fill="#FFFFFF"/>')
        if verdict:
            self.glyph(verdict, x + w / 2, y + h / 2, 6.5)

    def ledger_icon(self, x, y):
        self.rect(x, y, 26, 34, fill="#FFFFFF", stroke=GREY, sw=1.3, rx=2)
        for i in range(4):
            self.line([(x + 6, y + 9 + 6 * i), (x + 20, y + 9 + 6 * i)], color=GREY, sw=1.3)

    def person(self, cx, y, color=GREY):
        self.raw(f'<circle cx="{cx}" cy="{y + 6}" r="5.5" fill="{color}"/>')
        self.raw(f'<path d="M{cx - 10},{y + 24} Q{cx - 10},{y + 13} {cx},{y + 13} '
                 f'Q{cx + 10},{y + 13} {cx + 10},{y + 24} Z" fill="{color}"/>')

    def lock(self, cx, cy, color=S_LINE, open_=False):
        """Support gate: a small padlock."""
        sh = (f'M{cx - 4.5},{cy - 2} L{cx - 4.5},{cy - 6} A4.5,4.5 0 0 1 {cx + 4.5},{cy - 6} '
              f'L{cx + 4.5},{cy - 4}' if open_ else
              f'M{cx - 4.5},{cy - 2} L{cx - 4.5},{cy - 6} A4.5,4.5 0 0 1 {cx + 4.5},{cy - 6} '
              f'L{cx + 4.5},{cy - 2}')
        self.raw(f'<path d="{sh}" fill="none" stroke="{color}" stroke-width="2"/>')
        self.rect(cx - 7, cy - 2, 14, 11, fill=color, stroke="none", rx=2)

    def bubble(self, x, y, w, h):
        """Query: speech bubble."""
        self.raw(f'<path d="M{x + 8},{y} H{x + w - 8} Q{x + w},{y} {x + w},{y + 8} V{y + h - 8} '
                 f'Q{x + w},{y + h} {x + w - 8},{y + h} H{x + 22} L{x + 10},{y + h + 9} '
                 f'L{x + 12},{y + h} H{x + 8} Q{x},{y + h} {x},{y + h - 8} V{y + 8} '
                 f'Q{x},{y} {x + 8},{y} Z" fill="#FFFFFF" stroke="{ARROW}" stroke-width="1.6"/>')

    def robot(self, cx, y, color=GREY):
        """Answer model."""
        self.line([(cx, y), (cx, y + 6)], color=color, sw=1.6)
        self.raw(f'<circle cx="{cx}" cy="{y}" r="2.6" fill="{color}"/>')
        self.rect(cx - 13, y + 6, 26, 19, fill="#FFFFFF", stroke=color, sw=1.6, rx=4)
        for dx in (-5, 5):
            self.raw(f'<circle cx="{cx + dx}" cy="{y + 15}" r="2.4" fill="{color}"/>')

    # -- output ----------------------------------------------------------------------------
    def svg(self, title):
        def marker(mid, color, size):
            return (f'<marker id="{mid}" viewBox="0 0 10 10" refX="8" refY="5" '
                    f'markerWidth="{size}" markerHeight="{size}" markerUnits="userSpaceOnUse" '
                    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{color}"/>'
                    f'</marker>')
        defs = ("<defs>" + marker("a-big", ARROW, 15) + marker("a-big-s", S_LINE, 15)
                + marker("a-small", ARROW, 10) + marker("a-small-s", S_LINE, 10)
                + marker("a-small-g", GREY, 10) + marker("a-teal", TEAL, 10)
                + marker("a-amber", AMBER, 10) + "</defs>")
        roles = [("text", INK), ("secondary text", MUTED), ("SAFE-Mem line", GREY_L),
                 ("SAFE-Mem fill", GREY_F), ("S line / supported", S_LINE), ("S text", S_DARK),
                 ("S fill", S_FILL), ("S stage background", S_TINT),
                 ("S scope not supported", S_OFF_LINE), ("unsafe / withheld", RED),
                 ("unsafe fill", RED_F), ("arrows", ARROW), ("SL line", TEAL), ("SL text", TEAL_D),
                 ("SL fill", TEAL_F), ("S2-ID line", AMBER), ("S2-ID text", AMBER_D),
                 ("S2-ID fill", AMBER_F)]
        pal = "\n".join(f"  {v}  {k}" for k, v in roles)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {self.h}" '
                f'width="{W}" height="{self.h}">\n<title>{esc(title)}</title>\n'
                f'<!-- PALETTE (find-and-replace a hex to recolour that role)\n{pal}\n-->\n'
                f'{defs}\n<rect x="0" y="0" width="{W}" height="{self.h}" fill="#FFFFFF"/>\n'
                + "\n".join(self.el) + "\n</svg>\n")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


SI = {"serif": True, "italic": True}
S_ = {"serif": True}
MUT = {"fill": MUTED}
IT_M = {"fill": MUTED, "italic": True}


def sym(base, sub, fill=INK):
    return [(base, {**SI, "fill": fill}), (sub, {"serif": True, "sub": True, "fill": fill})]


def nsup(sign, fill=INK):
    return [("n", {**SI, "fill": fill}), (sign, {"serif": True, "sup": True, "fill": fill})]


def legend(f, x, y, items):
    """items: ('box', kind, label) | ('glyph', kind, label) | ('sep',)."""
    for it in items:
        if it[0] == "sep":
            f.line([(x + 2, y - 15), (x + 2, y + 3)], color=FAINT, sw=1.2)
            x += 18
            continue
        if it[0] == "box":
            f.pill(x, y - 14, 24, 17, it[1], dash="4 3" if it[1] == "amber" else None)
            x += 32
        else:
            f.glyph(it[1], x + 8, y - 6, 7.5)
            x += 21
        x += f.text(x, y, it[2], 17) + 22
    return x


# =======================================================================================
# Figure A: method overview
# =======================================================================================
def figure_a(ext=False):
    f = Fig("A", 436 + (138 if ext else 0))
    Y0, HH = 50, 334                     # stage boxes: top, height
    X1, W1 = 12, 372                     # 1 audit evidence
    X2, W2 = 428, 500                    # 2 selective propagation (ours)
    X3, W3 = 972, 406                    # 3 governed retrieval (SAFE-Mem)

    # ---- 1. audit evidence ------------------------------------------------------------
    f.group("A1-audit-evidence")
    f.header(X1 + 4, 32, 1, "Audit evidence")
    f.stage(X1, Y0, W1, HH)
    L = X1 + 18
    # a record and its trusted provenance (Eq. 1)
    f.rect(L, 70, 104, 40, fill="#FFFFFF", stroke=GREY_L, sw=1.3, rx=6)
    f.g_open(L + 20, 90)
    f.rich(L + 36, 97, [("record ", {}), ("x", SI)], size=18)
    for i, (sy, lab) in enumerate((("u", "contributor"), ("c", "context"), ("b", "batch"))):
        cx = L + 156 + 76 * i
        f.rect(cx - 26, 72, 52, 36, fill=GREY_F, stroke=GREY_L, sw=1.1, rx=6)
        f.rich(cx, 97, [(sy, {**SI})], size=21, anchor="middle")
        f.text(cx, 128, lab, 16, fill=MUTED, anchor="middle")
    f.line([(L + 106, 90), (L + 128, 90)], color=GREY_L, sw=1.4, dash="3 3")
    # a few audits on a mostly unaudited memory
    tiles = ["x", "o", "o", "x", "o", "safe", "o", "o", "x", "o"]
    tw, gap = 26, 8.2
    ty = 220
    f.rich(L, 160, [("T", {**SI, "fill": MUTED}),
                    (" audit tickets", {"weight": "bold", "fill": MUTED})], size=17)
    for i, k in enumerate(tiles):
        tx = L + i * (tw + gap)
        f.rect(tx, ty, tw, tw, fill="#FFFFFF", stroke=GREY_L, sw=1.1, rx=4)
        f.glyph(k, tx + tw / 2, ty + tw / 2, 7.5)
        if k != "o":
            f.ticket(tx + tw / 2 - 17, 172, w=34, h=20)
            f.flow(tx + tw / 2, 194, tx + tw / 2, ty - 3, color=GREY, sw=1.5)
    f.text(L + 10 * (tw + gap) - gap, 268, "most records stay unaudited", 16, italic=True,
           fill=MUTED, anchor="end")
    # evidence ledger
    f.flow(L + 40, 254, L + 40, 284, color=GREY, sw=2)
    f.rect(L, 288, W1 - 36, 84, fill=GREY_F, stroke=GREY_L, sw=1.3, rx=10)
    f.ledger_icon(L + 14, 306)
    f.text(L + 54, 319, "Evidence ledger", 20, "bold")
    f.text(L + 54, 344, "one vote per incident root", 17, fill=MUTED)
    f.inline(L + 54, 365, [*[(t, {**o, "fill": MUTED}) for t, o in nsup("−")], (" unsafe, ", MUT),
                           *[(t, {**o, "fill": MUTED}) for t, o in nsup("+")], (" safe roots", MUT)],
             size=17, maxw=W1 - 90)
    f.end()

    # ---- 2. selective propagation (ours) ----------------------------------------------
    f.group("A2-selective-propagation-S")
    f.header(X2 + 4, 32, 2, "Selective propagation  S (ours)", color=S_DARK)
    f.stage(X2, Y0, W2, HH, ours=True)
    # nested scopes of record x (Eq. 5); a scope joins only through its gate (Eq. 9)
    rx0, ry0 = X2 + 18, 66
    for (x_, y_, w_, h_, fill) in ((rx0, ry0, 262, 238, "#FFFFFF"),
                                   (rx0 + 22, ry0 + 50, 218, 176, S_TINT),
                                   (rx0 + 44, ry0 + 100, 174, 114, S_FILL)):
        f.rect(x_, y_, w_, h_, fill=fill, stroke=S_LINE, sw=1.5, rx=10)
    # labels + gates on each ring
    f.rich(rx0 + 12, ry0 + 24, [("contributor ", {"weight": "bold", "fill": S_DARK}),
                                ("u", {**SI, "fill": S_DARK})], size=18)
    f.rich(rx0 + 34, ry0 + 74, [("context ", {"weight": "bold", "fill": S_DARK}),
                                ("c", {**SI, "fill": S_DARK})], size=18)
    f.rich(rx0 + 56, ry0 + 124, [("batch ", {"weight": "bold", "fill": S_DARK}),
                                 ("b", {**SI, "fill": S_DARK})], size=18)
    for gx, gy in ((rx0 + 262 - 22, ry0 + 18), (rx0 + 22 + 218 - 22, ry0 + 68),
                   (rx0 + 44 + 174 - 22, ry0 + 118)):
        f.lock(gx, gy)
    # verified incidents and the record being decided, inside the batch
    bx_, by_ = rx0 + 60, ry0 + 170
    f.g_x(bx_ + 8, by_ + 8)
    f.g_x(bx_ + 30, by_ + 8)
    f.rect(bx_ + 52, by_ - 6, 70, 28, fill="#FFFFFF", stroke=GREY_L, sw=1.2, rx=6)
    f.g_open(bx_ + 66, by_ + 8)
    f.rich(bx_ + 80, by_ + 14, [("x", SI)], size=19)
    # gate rule (the one idea of S)
    gl = rx0 + 10
    f.lock(gl + 8, 330)
    f.text(gl + 24, 334, "a scope opens only when", 18, fill=S_DARK)
    f.text(gl + 24, 357, "verified incidents span it", 18, "bold", fill=S_DARK)
    # risk -> penalty -> D (Eqs. 6-7)
    cx_ = X2 + 304
    cw_ = X2 + W2 - 16 - cx_
    f.text(cx_, 90, "per supported scope", 17, italic=True, fill=MUTED)
    f.rich(cx_, 120, [("r", SI), (" = (1+", S_), *nsup("−"), (") / (2+", S_), *nsup("−"),
                      ("+", S_), *nsup("+"), (")", S_)], size=20, maxw=cw_)
    f.rich(cx_, 152, [("d", SI), (" = max(0, ", S_), ("r", SI), (" − ½)", S_)], size=20,
           maxw=cw_)
    f.line([(cx_, 172), (cx_ + cw_, 172)], color=S_OFF_LINE, sw=1)
    f.text(cx_, 198, "per record", 17, italic=True, fill=MUTED)
    f.rich(cx_, 228, [("D", {**SI, "fill": S_DARK}), (" = max of ", {"fill": S_DARK}),
                      ("d", {**SI, "fill": S_DARK})], size=20, maxw=cw_)
    f.rich(cx_, 254, [("D", {**SI, "fill": MUTED}), (" = 0 if none", MUT)],
           size=16, maxw=cw_)
    f.end()

    # ---- 3. governed retrieval (SAFE-Mem) ---------------------------------------------
    f.group("A3-governed-retrieval")
    f.header(X3 + 4, 32, 3, "Governed retrieval (SAFE-Mem)", maxw=W3 - 36)
    f.stage(X3, Y0, W3, HH)
    px, pw = X3 + 70, W3 - 92
    f.bubble(X3 + 14, 66, 44, 28)
    f.rich(X3 + 36, 86, [("q", SI)], size=19, anchor="middle")
    f.robot(X3 + 36, 294)
    steps = [  # (y, h, kind, lines)
        (66, 42, "grey", [[("Admission  ", {}), ("α", SI), ("(", S_), ("x", SI), (", ", S_),
                           ("q", SI), (")", S_)]]),
        (132, 66, "ours", [[("audited ", {"fill": S_DARK}), ("@", "x"),
                            ("  or  ", {"fill": S_DARK}), ("D", {**SI, "fill": S_DARK}),
                            (" ≥ ", {"fill": S_DARK}), ("τ", {**SI, "fill": S_DARK}),
                            ("  →  ", {"fill": S_DARK}),
                            ("withhold", {"weight": "bold", "fill": RED})],
                           [("else rank by  ", {"fill": S_DARK}), ("s", {**SI, "fill": S_DARK}),
                            (" − ", {"fill": S_DARK}), ("λD", {**SI, "fill": S_DARK})]]),
        (222, 42, "light", [[("serve top ", {}), ("k", SI), (" claims + ", {}), ("m", SI),
                             (" chunks", {})]]),
        (288, 42, "grey", [[("conflict check → answer model", {})]]),
    ]
    for i, (y, h, kind, lines) in enumerate(steps):
        f.pill(px, y, pw, h, kind)
        for j, parts in enumerate(lines):
            base = y + h / 2 + 6.5 - (len(lines) - 1) * 12.5 + j * 25
            f.inline(px + pw / 2, base, parts, size=18, anchor="middle", maxw=pw - 16)
        if i < len(steps) - 1:
            f.flow(px + pw / 2, y + h + 2, px + pw / 2, steps[i + 1][0] - 3)
    f.text(px + pw - 6, 218, "freed slots refilled", 16, italic=True, fill=S_DARK, anchor="end")
    f.flow(X3 + 58, 80, px - 3, 86)                   # query into admission
    f.flow(px - 3, 309, X3 + 54, 309)                 # served context to the answer model
    f.end()

    # ---- stage arrows -----------------------------------------------------------------
    f.stage_arrow(X1 + W1 + 6, X2 - 6, 330)
    f.stage_arrow(X2 + W2 + 6, px - 4, 165, color=S_LINE)
    f.rich((X2 + W2 + X3) / 2 + 2, 153, [("D", {**SI, "fill": S_DARK})], size=19,
           anchor="middle")

    if ext:
        extensions(f, X2, X3, px, pw)

    # ---- legend ------------------------------------------------------------------------
    boxes = [("box", "ours", "S (ours)"), ("box", "grey", "SAFE-Mem (unchanged)")]
    if ext:
        boxes += [("box", "teal", "SL"), ("box", "amber", "S2-ID")]
    legend(f, 14, f.h - 14, [*boxes, ("sep",), ("glyph", "x", "audited unsafe"),
                             ("glyph", "safe", "audited safe"), ("glyph", "o", "unaudited")])
    return f


def extensions(f, X2, X3, px, pw):
    """SL and S2-ID, hooked where the code applies them.
    SL  = S + content-lineage veto inside each candidate decision (lineage.py, LineagePolicy).
    S2-ID = SL + MemLineage's sensitive-query gate on the final context (sv2.py, _GatedReader)."""
    f.group("A4-exploratory-extensions")
    top, h = 410, 104
    f.text(14, top + 30, "Exploratory extensions", 20, "bold")
    f.text(14, top + 54, "Appendix C; composable:", 17, fill=MUTED)
    f.inline(14, top + 80, [("S", {"weight": "bold", "fill": S_DARK}), ("  →  ", MUT),
                            ("SL", {"weight": "bold", "fill": TEAL_D}), ("  →  ", MUT),
                            ("S2-ID", {"weight": "bold", "fill": AMBER_D})], size=18)
    # SL box
    sx, sw = X2, 520
    f.rect(sx, top, sw, h, fill=TEAL_F, stroke=TEAL, sw=1.8, rx=12)
    f.text(sx + 16, top + 28, "SL: content-lineage veto", 19, "bold", fill=TEAL_D)
    tx = sx + 16
    f.rect(tx, top + 42, 96, 28, fill="#FFFFFF", stroke=GREY_L, sw=1.2, rx=6)
    f.g_open(tx + 15, top + 56, 7)
    f.text(tx + 28, top + 62, "relay", 17, "bold", fill=RED)
    f.line([(tx + 100, top + 56), (tx + 196, top + 56)], color=TEAL, sw=1.8, dash="1.5 3.5")
    f.rich(tx + 148, top + 50, [("cos ≥ ", {"fill": TEAL_D}), ("η", {**SI, "fill": TEAL_D})], size=16,
           anchor="middle")
    f.rect(tx + 200, top + 42, 150, 28, fill="#FFFFFF", stroke=GREY_L, sw=1.2, rx=6)
    f.g_x(tx + 215, top + 56, 7)
    f.text(tx + 228, top + 62, "unsafe-audited", 17, fill=INK)
    f.text(tx + 362, top + 62, "→ vetoed", 17, "bold", fill=TEAL_D)
    f.rich(sx + 16, top + 92, [("gap: an unlinked near-copy is a new root, so S gives it ", IT_M),
                               ("D", {**SI, "fill": MUTED}), (" = 0", IT_M)], size=16, maxw=sw - 30)
    # S2-ID box
    ax, aw = X3, 406
    f.rect(ax, top, aw, h, fill=AMBER_F, stroke=AMBER, sw=1.8, rx=12, dash="6 4")
    f.text(ax + 16, top + 28, "S2-ID: SL + MemLineage gate", 19, "bold", fill=AMBER_D, maxw=aw - 30)
    f.inline(ax + 16, top + 62, [("sensitive query", {"weight": "bold"}), (" + any non-principal", {})],
             size=17, maxw=aw - 30)
    f.inline(ax + 16, top + 92, [("memory  →  context ", {}), ("∅", {"serif": True, "weight": "bold",
                                                                     "fill": AMBER_D})],
             size=17, maxw=aw - 190)
    f.text(ax + aw - 14, top + 92, "identity-blind (Sybils)", 16, italic=True, fill=MUTED,
           anchor="end")
    # hooks: SL into the S decision step; S2-ID on the final context before the answer model
    gx = (X2 + 500 + X3) / 2 + 4
    f.line([(sx + sw, top + 56), (gx, top + 56), (gx, 186), (px - 4, 186)], color=TEAL, sw=1.8,
           dash="5 3", marker="a-teal")
    dx, dy = X3 + 62, 309
    f.raw(f'<path d="M{dx},{dy - 8} L{dx + 8},{dy} L{dx},{dy + 8} L{dx - 8},{dy} Z" fill="{AMBER}"/>')
    f.line([(dx, top - 2), (dx, dy + 12)], color=AMBER, sw=1.8, dash="5 3", marker="a-amber")
    f.end()


# =======================================================================================
# Figure B: worked example (toy ledger of the earlier figure; outcomes = frozen code)
# =======================================================================================
def figure_b():
    f = Fig("B", 626)
    C0, C1, C2, C3, C4 = (12, 140), (188, 266), (490, 240), (766, 310), (1112, 266)
    ROWS = (52, 270)                     # row tops
    RH = 200                             # row height

    # column headers
    for n, (x, w), lab, col in ((1, C1, "Unaudited record", INK), (2, C2, "A’s audit evidence", INK),
                                (3, C3, "Supported scopes → D", S_DARK),
                                (4, C4, "Retrieval decision", INK)):
        f.header(x, 32, n, lab, color=col, maxw=w - 34)

    rows = [
        dict(label="Planted claim", tag="attack", tagc=RED, claim="Project code: ZX-91",
             claimc=RED, b="1", cell=(0, 0), nline=[("batch 1:  ", {"weight": "bold"}),
                                                     *nsup("−"), (" = 2,  ", S_), *nsup("+"),
                                                     (" = 0", S_)],
             gates=[("batch", True, [("2 ", {}), ("@", "x"), (" ≥ ", {}), *sym("θ", "bat")]),
                    ("context", False, [("@", "x"), (" in 1 batch < ", MUT),
                                        *sym("δ", "ctx", MUTED)]),
                    ("contributor", False, [("0 qualifying < ", MUT), *sym("δ", "src", MUTED)])],
             D=[("r", SI), (" = 3/4,  ", S_), ("d", SI), (" = 1/4  →  ", S_),
                ("D", {**SI, "weight": "bold", "fill": S_DARK}),
                (" = 1/4", {"serif": True, "weight": "bold", "fill": S_DARK})],
             q="Q1: project code?"),
        dict(label="Useful note", tag="benign", tagc=S_DARK, claim="Larkspur review: Wed.",
             claimc=S_DARK, b="2", cell=(0, 1), nline=[("batch 2:  no ", {"weight": "bold"}),
                                                        ("@", "x")],
             gates=[("batch", False, [("0 ", MUT), ("@", "x"), (" in batch 2", MUT)]),
                    ("context", False, [("@", "x"), (" in 1 batch < ", MUT),
                                        *sym("δ", "ctx", MUTED)]),
                    ("contributor", False, [("0 qualifying < ", MUT), *sym("δ", "src", MUTED)])],
             D=[("no supported scope  →  ", {}),
                ("D", {**SI, "weight": "bold", "fill": S_DARK}),
                (" = 0", {"serif": True, "weight": "bold", "fill": S_DARK})],
             q="Q2: Larkspur review?"),
    ]

    for ri, R in enumerate(rows):
        top = ROWS[ri]
        mid = top + RH / 2
        f.group(f"B-row{ri + 1}")
        # row label
        x, w = C0
        f.rect(x, top + 52, w, 96, fill=RED_F if ri == 0 else S_FILL,
               stroke=RED if ri == 0 else S_LINE, sw=2, rx=12)
        f.text(x + w / 2, mid - 4, R["label"], 20, "bold", anchor="middle", maxw=w - 12)
        f.text(x + w / 2, mid + 21, R["tag"], 17, italic=True, fill=R["tagc"], anchor="middle")

        # 1 record + provenance
        x, w = C1
        f.stage(x, top, w, RH)
        f.rect(x + 16, top + 40, w - 32, 50, fill="#FFFFFF", stroke=GREY_L, sw=1.3, rx=10)
        f.g_open(x + 34, top + 65)
        f.text(x + 50, top + 72, R["claim"], 17, "bold", fill=R["claimc"], maxw=w - 68)
        for i, (sy, val) in enumerate((("u", "A"), ("c", "X"), ("b", R["b"]))):
            cx = x + 56 + 77 * i
            f.rect(cx - 32, top + 118, 64, 34, fill=GREY_F, stroke=GREY_L, sw=1.1, rx=6)
            f.rich(cx, top + 141, [(sy, SI), (" = ", S_), (val, {"weight": "bold"})], size=18,
                   anchor="middle")

        # 2 A's evidence: contexts x batches (one vote per root)
        x, w = C2
        f.stage(x, top, w, RH)
        gx, gy, cw_, ch_ = x + 42, top + 46, 88, 40
        for j, b in enumerate(("b1", "b2")):
            f.text(gx + cw_ * j + cw_ / 2, gy - 10, b, 17, "bold", fill=MUTED, anchor="middle")
        cells = {(0, 0): ["x", "x", "o*"], (0, 1): ["o*"], (1, 0): ["x", "x"], (1, 1): ["o", "o"]}
        for i, c in enumerate(("X", "Y")):
            f.text(gx - 14, gy + ch_ * i + ch_ / 2 + 6, c, 18, "bold", fill=MUTED, anchor="end")
            for j in range(2):
                hl = (i, j) == R["cell"]
                f.rect(gx + cw_ * j + 3, gy + ch_ * i + 3, cw_ - 6, ch_ - 6,
                       fill=S_FILL if hl else "#FFFFFF", stroke=S_LINE if hl else GREY_L,
                       sw=2.4 if hl else 1.1, rx=6)
                ks = cells[(i, j)]
                for k, kind in enumerate(ks):
                    this = kind == "o*"
                    show = this and (i, j) == R["cell"]
                    kk = "o" if this else kind
                    cx = gx + cw_ * j + cw_ / 2 + (k - (len(ks) - 1) / 2) * 21
                    if this and not show:
                        f.g_open(cx, gy + ch_ * i + ch_ / 2, 7)
                    else:
                        f.glyph(kk, cx, gy + ch_ * i + ch_ / 2, 8)
                    if show:
                        f.raw(f'<circle cx="{cx:.1f}" cy="{gy + ch_ * i + ch_ / 2:.1f}" r="11.5" '
                              f'fill="none" stroke="{R["claimc"]}" stroke-width="1.6"/>')
        f.inline(x + 16, top + 168, R["nline"], size=18, maxw=w - 28)

        # 3 supported scopes -> D  (ours)
        x, w = C3
        f.stage(x, top, w, RH, ours=True)
        for gi, (nm, on, why) in enumerate(R["gates"]):
            y = top + 16 + gi * 38
            f.pill(x + 14, y, w - 28, 32, "ours" if on else "off", dash=None if on else "4 3")
            f.glyph("ok" if on else "off", x + 32, y + 16, 8)
            f.text(x + 46, y + 22, nm, 17, "bold", fill=S_DARK if on else S_OFF_TEXT)
            f.inline(x + 150, y + 22, why, size=17, maxw=w - 164)
        f.line([(x + 14, top + 140), (x + w - 14, top + 140)], color=S_OFF_LINE, sw=1)
        f.rich(x + w / 2, top + 174, R["D"], size=19, anchor="middle", maxw=w - 24)

        # 4 retrieval decision + served context
        x, w = C4
        f.stage(x, top, w, RH)
        if ri == 0:
            f.pill(x + 14, top + 14, w - 28, 34, "red")
            f.inline(x + 28, top + 37, [("D", {**SI, "fill": RED}), (" ≥ ", {"fill": RED}),
                                        ("τ", {**SI, "fill": RED}), ("  →  ", {"fill": RED}),
                                        ("withheld", {"weight": "bold", "fill": RED})],
                     size=18, maxw=w - 50)
        else:
            f.pill(x + 14, top + 14, w - 28, 34, "ours")
            f.inline(x + 28, top + 37, [("D", {**SI, "fill": S_DARK}), (" < ", {"fill": S_DARK}),
                                        ("τ", {**SI, "fill": S_DARK}), ("  →  ", {"fill": S_DARK}),
                                        ("kept", {"weight": "bold", "fill": S_DARK})],
                     size=18, maxw=w - 50)
        f.text(x + 16, top + 76, R["q"], 17, "bold", fill=MUTED, maxw=w - 76)
        f.text(x + w - 16, top + 76, "top k", 16, italic=True, fill=MUTED, anchor="end")
        sw_, sh_ = 112, 24
        for si in range(4):
            col, rr = si % 2, si // 2
            sx, sy = x + 16 + col * (sw_ + 8), top + 88 + rr * (sh_ + 8)
            if ri == 0 and si == 3:
                f.rect(sx, sy, sw_, sh_, fill=S_TINT, stroke=S_LINE, sw=1.3, rx=5, dash="4 3")
                f.text(sx + sw_ / 2, sy + 17, "refill", 16, fill=S_DARK, anchor="middle")
            elif ri == 1 and si == 0:
                f.rect(sx, sy, sw_, sh_, fill=S_FILL, stroke=S_LINE, sw=1.6, rx=5)
                f.g_ok(sx + 13, sy + sh_ / 2, 7)
                f.text(sx + 25, sy + 17, "Larkspur", 16, "bold", fill=S_DARK, maxw=sw_ - 28)
            else:
                f.rect(sx, sy, sw_, sh_, fill=GREY_F, stroke="#D6D6D6", sw=1, rx=5)
        if ri == 0:
            f.g_x(x + 30, top + 172, 7.5)
            f.text(x + 44, top + 178, "ZX-91 not served", 17, fill=RED, maxw=w - 60)
        else:
            f.text(x + 16, top + 178, "useful note still served", 17, fill=S_DARK, maxw=w - 30)
        f.end()

        # column arrows
        for (xa, wa), (xb, _) in ((C1, C2), (C2, C3), (C3, C4)):
            f.stage_arrow(xa + wa + 5, xb - 5, mid, color=S_LINE if xb == C4[0] else ARROW)

    # bracket: same contributor and context
    f.line([(C0[0] + C0[1] / 2, ROWS[0] + 150), (C0[0] + C0[1] / 2, ROWS[1] + 50)],
           color=GREY_L, sw=1.4, dash="3 3")
    f.rect(C0[0] + 4, (ROWS[0] + RH + ROWS[1]) / 2 - 26, C0[1] - 8, 50, fill="#FFFFFF",
           stroke="none")
    f.text(C0[0] + C0[1] / 2, (ROWS[0] + RH + ROWS[1]) / 2 - 6, "same contributor A,", 16,
           fill=MUTED, anchor="middle", maxw=C0[1])
    f.text(C0[0] + C0[1] / 2, (ROWS[0] + RH + ROWS[1]) / 2 + 14, "same context X", 16,
           fill=MUTED, anchor="middle", maxw=C0[1])

    # baselines on the same two records (frozen Policy.decide on this toy ledger)
    f.group("B-baselines")
    by = 500
    f.text(C1[0], by + 18, "Same two records,", 18, "bold", fill=MUTED)
    f.text(C1[0], by + 42, "other policies:", 18, "bold", fill=MUTED)
    pol = [("R", "record-local", ("leak", "leaks", RED), ("ok", "kept", INK)),
           ("C", "contributor-context", ("x", "withheld", INK), ("x", "lost", RED)),
           ("M", "maximal", ("x", "withheld", INK), ("x", "lost", RED)),
           ("S", "selective (ours)", ("x", "withheld", INK), ("ok", "kept", S_DARK))]
    x0, cw = C2[0], 216
    f.text(x0 - 14, by + 30, "ZX-91", 17, "bold", fill=RED, anchor="end")
    f.text(x0 - 14, by + 58, "Larkspur", 17, "bold", fill=S_DARK, anchor="end")
    for i, (m, desc, a, b) in enumerate(pol):
        x = x0 + i * (cw + 6)
        ours = m == "S"
        f.rect(x, by - 18, cw, 88, fill=S_FILL if ours else "#FFFFFF",
               stroke=S_LINE if ours else GREY_L, sw=2.2 if ours else 1.2, rx=10)
        f.text(x + 12, by + 2, m, 19, "bold", fill=S_DARK if ours else INK)
        f.text(x + 34, by + 2, desc, 16, italic=True, fill=S_DARK if ours else MUTED,
               maxw=cw - 42)
        for j, (kind, word, col) in enumerate((a, b)):
            f.glyph(kind, x + 22, by + 24 + j * 28, 7.5)
            f.text(x + 36, by + 30 + j * 28, word, 17, "bold" if col == RED or ours else "normal",
                   fill=col, maxw=cw - 44)
    f.end()
    legend(f, 14, 612, [("box", "ours", "S (ours)"), ("box", "grey", "SAFE-Mem / baselines"),
                        ("sep",), ("glyph", "x", "unsafe / withheld"),
                        ("glyph", "o", "unaudited"), ("glyph", "ok", "supported / kept"),
                        ("glyph", "off", "not supported"), ("glyph", "leak", "leaks")])
    return f


# =======================================================================================
# Figure C: the method itself -- how far distrust spreads as verified evidence grows.
# Values: frozen Policy.decide, main setting, n+ = 0 (scratch check, README "Figure C").
# =======================================================================================
def figure_c():
    f = Fig("C", 430)
    BW, GAP, Y0, HH = 424, 47, 50, 334
    XS = [12 + i * (BW + GAP) for i in range(3)]
    stages = [
        dict(head="One incident", inc={("X", 0)},
             gate=[("batch: ≥ ", {}), *sym("θ", "bat"), (" ", {}), ("@", "x"), (" in the batch", {})],
             scope="cell", out={("X", 0): "down"},
             calc=[("batch b1:  ", {"weight": "bold", "fill": S_DARK}), *nsup("−"), (" = 1  →  ", S_),
                   ("D", SI), (" = 1/6 < ", S_), ("τ", SI)],
             res="down-rank batch b1 only"),
        dict(head="Recurs across batches", inc={("X", 0), ("X", 1)},
             gate=[("+ context: ≥ ", {}), *sym("θ", "ctx"), (" ", {}), ("@", "x"), (" in ≥ ", {}),
                   *sym("δ", "ctx"), (" batches", {})],
             scope="row", out={("X", 0): "w", ("X", 1): "w"},
             calc=[("context X:  ", {"weight": "bold", "fill": S_DARK}), *nsup("−"), (" = 2  →  ", S_),
                   ("D", SI), (" = 1/4 ≥ ", S_), ("τ", SI)],
             res="withhold all of context X"),
        dict(head="Recurs across contexts", inc={("X", 0), ("X", 1), ("Y", 0), ("Y", 1)},
             gate=[("+ contributor: ≥ ", {}), *sym("θ", "src"), (" ", {}), ("@", "x"), (", ≥ ", {}),
                   *sym("δ", "src"), (" qualifying*", {})],
             scope="all", out={(c, b): "w" for c in "XYZ" for b in (0, 1)},
             calc=[("contributor A:  ", {"weight": "bold", "fill": S_DARK}), *nsup("−"),
                   (" = 4  →  ", S_), ("D", SI), (" = 1/3 ≥ ", S_), ("τ", SI)],
             res="withhold all of A, even context Z"),
    ]
    rows = ("X", "Y", "Z")
    for i, st in enumerate(stages):
        x = XS[i]
        f.group(f"C-stage{i + 1}")
        f.header(x + 4, 32, i + 1, st["head"], color=S_DARK, maxw=BW - 36)
        f.stage(x, Y0, BW, HH, ours=True)
        f.inline(x + 16, Y0 + 30, [(t, o) if t == "@" else (t, {**o, "fill": o.get("fill", S_DARK)})
                                   for t, o in st["gate"]], size=17, maxw=BW - 30)
        gx, gy, cw, ch = x + 52, Y0 + 70, 172, 50
        for j, b in enumerate(("b1", "b2")):
            f.text(gx + cw * j + cw / 2, gy - 8, b, 17, "bold", fill=MUTED, anchor="middle")
        for r, c in enumerate(rows):
            f.text(gx - 14, gy + ch * r + ch / 2 + 6, c, 18, "bold", fill=MUTED, anchor="end")
            for j in range(2):
                cx, cy = gx + cw * j, gy + ch * r
                f.rect(cx + 3, cy + 3, cw - 6, ch - 6, fill="#FFFFFF", stroke="#DADADA", sw=1, rx=6)
                if (c, j) in st["inc"]:
                    f.g_x(cx + 22, cy + ch / 2, 8)
                kind = st["out"].get((c, j), "keep")
                tx, tw_ = cx + 40, cw - 50
                fill, stroke, col, lab = {"keep": ("#FFFFFF", GREY_L, MUTED, "kept"),
                                          "down": (S_FILL, S_LINE, S_DARK, "penalised"),
                                          "w": (RED_F, RED, RED, "withheld")}[kind]
                f.rect(tx, cy + 10, tw_, ch - 20, fill=fill, stroke=stroke, sw=1.3, rx=5)
                f.g_open(tx + 13, cy + ch / 2, 6.5)
                f.text(tx + 25, cy + ch / 2 + 6, lab, 16, "bold" if kind != "keep" else "normal",
                       fill=col, maxw=tw_ - 28)
        # supported scope outline (widest one)
        if st["scope"] == "cell":
            ox, oy, ow, oh = gx - 1, gy - 1, cw + 2, ch + 2
        elif st["scope"] == "row":
            ox, oy, ow, oh = gx - 1, gy - 1, 2 * cw + 2, ch + 2
        else:
            ox, oy, ow, oh = gx - 40, gy - 30, 2 * cw + 48, 3 * ch + 36
        f.rect(ox, oy, ow, oh, fill="none", stroke=S_LINE, sw=2.6, rx=9)
        f.line([(x + 16, Y0 + 250), (x + BW - 16, Y0 + 250)], color=S_OFF_LINE, sw=1)
        f.rich(x + 16, Y0 + 278, st["calc"], size=18, maxw=BW - 30)
        f.text(x + 16, Y0 + 308, st["res"], 18, "bold",
               fill=S_DARK if i == 0 else RED, maxw=BW - 30)
        f.end()
        if i < 2:
            f.stage_arrow(x + BW + 6, XS[i + 1] - 6, gy + ch * 1.5)
    legend(f, 14, 416, [("box", "ours", "supported scope"), ("sep",), ("glyph", "x", "audited unsafe"),
                        ("glyph", "o", "unaudited record:"), ("box", "white", "kept"),
                        ("box", "ours", "penalised (ranked lower)"), ("box", "red", "withheld")])
    f.inline(W - 290, 416, [("* qualifying: ≥ ", IT_M), *sym("θ", "Q", MUTED), (" ", IT_M), ("@", "x"),
                           (" in ≥ ", IT_M), *sym("δ", "Q", MUTED), (" batches", IT_M)], size=16)
    return f


def main():
    out = {"fig_A_overview.svg": (figure_a, "Selective evidence propagation: overview"),
           "fig_A_family.svg": (lambda: figure_a(ext=True),
                                "Selective evidence propagation and its exploratory extensions"),
           "fig_B_example.svg": (figure_b, "Selective evidence propagation: worked example"),
           "fig_C_spread.svg": (figure_c, "Selective evidence propagation: how far distrust spreads")}
    for path, (build, title) in out.items():
        f = build()
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(f.svg(title))
        for w_ in f.warn:
            print("WARN", path, w_.encode("ascii", "replace").decode(), file=sys.stderr)
        print(f"wrote {path} ({len(f.warn)} warnings)")


if __name__ == "__main__":
    main()
