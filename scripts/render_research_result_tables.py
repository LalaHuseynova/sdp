#!/usr/bin/env python3
"""Render verified result tables; no inference, annotation or experiment execution.

Use separate PDF tooling, not the frozen experiment environment:
    tmp/pdfs/result_table_tools/bin/python scripts/render_research_result_tables.py \
        --out tmp/pdfs/result_tables_draft --dpi 600
"""

import argparse
import hashlib
import importlib.metadata
import json
import re
import socket
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
FONT_ROOT = Path("/System/Library/Fonts/Supplemental")
WIDTH, MARGIN = 1056, 24
FONTS = {
    "regular": "Times New Roman.ttf",
    "bold": "Times New Roman Bold.ttf",
    "italic": "Times New Roman Italic.ttf",
}
METRICS = ["asr", "retention", "restraint", "combined_benign"]
LABELS = ["ASR ↓", "Recall ↑", "Restraint ↑", "Utility ↑"]
DIRECTIONS = ["min", "max", "max", "max"]
ARMS = [
    ("no_memory", "No memory (control)"),
    ("static", "Original SAFE-Mem (static)"),
    ("R", "Record-only (R)"),
    ("C", "Contextual reputation (C)"),
    ("M", "Fixed multi-scope (M)"),
    ("S", "Selective propagation (ours)"),
]
REGIMES = [
    ("strong_distributed", "Distributed"),
    ("strong_localized", "Localized"),
    ("uninformative", "Uninformative"),
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def read(relative):
    return json.loads((REPO / relative).read_text())


def number(n, den, precision=2):
    require(
        type(n) is int and type(den) is int and 0 <= n <= den and den > 0,
        "Invalid reported fraction",
    )
    value = Fraction(100 * n, den)
    return {
        "fraction": [n, den],
        "exact_percent": str(value),
        "display": f"{float(value):.{precision}f}",
        "best": False,
    }


def printed(value, precision=1):
    return {
        "fraction": None,
        "exact_percent": str(Fraction(str(value))),
        "display": f"{value:.{precision}f}",
        "best": False,
    }


def missing(reason):
    return {
        "fraction": None,
        "exact_percent": None,
        "display": "-",
        "best": False,
        "unavailable_reason": reason,
    }


def mark_best(table):
    for i, column in enumerate(table["columns"]):
        available = [
            Fraction(r["cells"][i]["exact_percent"])
            for r in table["rows"]
            if r["cells"][i]["exact_percent"] is not None
        ]
        best = (min if column["direction"] == "min" else max)(available) if available else None
        for row in table["rows"]:
            cell = row["cells"][i]
            cell["best"] = (
                cell["exact_percent"] is not None and Fraction(cell["exact_percent"]) == best
            )
    require(table["rows"][-1]["key"] == "S", "Proposed method must be the last row")


def extract_tables():
    import pymupdf

    original = read("reports/safemem_full_mpbench/final_results.json")
    published = read("reports/mpbench_published_targets.json")
    pilot = read("research_data/development_comparison_report_v1_20261101/comparison.json")
    audit = read("reports/RESEARCH_AUDIT_20261101_ARTIFACT_CHECKS_V2.json")
    delivery = read("reports/PROVISIONAL_RESULTS_20261101_DELIVERY.json")
    require(
        original["status"] == "full_validated"
        and original["source_records_ingested"] == 6240
        and original["readable_outcomes"] == 5996,
        "Original run is not complete",
    )
    require(
        pilot["status"] == "complete_saved_outcomes"
        and pilot["recorded_query_outcomes"] == 3888
        and pilot["independent_base_groups"] == 8
        and not pilot["scientifically_human_validated"],
        "Unexpected pilot scope",
    )
    require(
        audit["original_reproduction_recount"]["status"] == "passed"
        and audit["independent_result_recount"]["saved_outcomes_checked"] == 3888,
        "Independent recount missing",
    )
    result_path = "research_data/development_comparison_report_v1_20261101/comparison.json"
    require(sha(REPO / result_path) == delivery["files"][result_path], "Pilot data changed")
    target = next(
        r
        for r in published["published_targets"]
        if r["method"] == "safe_mem" and r["backbone"] == "4omini"
    )
    paper_path = REPO / "safe-mem_paper.pdf"
    with pymupdf.open(paper_path) as paper:
        found = []
        for i, page in enumerate(paper):
            text = page.get_text()
            match = re.search(
                r"SAFE-Mem\s+((?:\d+(?:\.\d+)?\s+){15}\d+(?:\.\d+)?)\s+Table 1:", text
            )
            if match:
                values = [float(n) for n in match[1].split()]
                found.append((i + 1, values, text))
        require(len(found) == 1, "Cannot uniquely locate paper Table 1")
        paper_page, paper_values, paper_text = found[0]
        require(
            re.search(r"1,540\s+recall\s+questions", paper_text), "LoCoMo sample size unverified"
        )
    paper_rates = [paper_values[1], paper_values[5], paper_values[9]]
    require(
        paper_rates == [target[k] for k in ["asr_percent", "recall_percent", "restraint_percent"]],
        "Paper PDF and target audit disagree",
    )
    original_keys = ["asr", "retention_recall", "restraint", "combined_benign_utility"]
    actual = [original["metrics"][k] for k in original_keys]
    for k, value in zip(METRICS, actual, strict=True):
        require(
            [value["numerator"], value["denominator"]]
            == audit["original_reproduction_recount"]["metrics"][k],
            "Original count mismatch",
        )
        require(
            abs(value["percent"] - 100 * value["numerator"] / value["denominator"]) < 1e-10,
            "Original percentage differs from count",
        )

    first = {
        "stem": "table_1_original_safemem_reproduction",
        "title": "Original SAFE-Mem: full-dataset reproduction",
        "subtitle": "GPT-4o-mini | MPBench: 6,240 source inputs; 5,996 readable questions",
        "groups": [
            {"label": "MPBench (full dataset)", "start": 0, "count": 4},
            {"label": "LoCoMo (paper)", "start": 4, "count": 1},
        ],
        "columns": [
            {"label": label, "direction": direction, "sample": f"n = {a['denominator']:,}"}
            for label, direction, a in zip(LABELS, DIRECTIONS, actual, strict=True)
        ]
        + [{"label": "Accuracy ↑", "direction": "max", "sample": "paper n = 1,540"}],
        "method_width": 292,
        "column_widths": [143, 143, 143, 143, 144],
        "rows": [
            {
                "key": "paper",
                "label": "Original SAFE-Mem (paper)",
                "cells": [printed(x) for x in paper_rates]
                + [
                    missing("Combined benign utility is not reported in paper Table 1"),
                    printed(paper_values[13]),
                ],
            },
            {
                "key": "reproduction",
                "label": "Original SAFE-Mem (reproduced)",
                "cells": [number(a["numerator"], a["denominator"]) for a in actual]
                + [missing("LoCoMo was not reproduced in this run")],
            },
            {
                "key": "S",
                "label": "Selective propagation (ours)",
                "cells": [
                    missing("Proposed defense has not been evaluated on full MPBench or LoCoMo")
                    for _ in range(5)
                ],
            },
        ],
        "caption": [
            "<b>Table 1.</b> Rates (%). Published SAFE-Mem results versus our reproduction; "
            "paper rates retain one decimal, reproduced rates use two. "
            "Metric denominators are shown above.",
            "<b>Bold:</b> best available entry per column, including ties. "
            "<b>-</b>: unavailable; singleton bold entries do not establish superiority. "
            "Utility = combined benign memory-use score.",
            "LoCoMo is a paper-only reference, not a reproduced result. "
            "All 244 write-only MPBench inputs remain in the pool; only reads are scored. "
            "Reproduction uses OpenRouter/current GPT-4o-mini.",
            "<b>Our proposed defense has NOT been evaluated on the full "
            "6,240-case MPBench dataset.</b>",
            f"<i>Sources:</i> SAFE-Mem v2, Table 1 and Sec. 5.1 (PDF p. {paper_page}); "
            "verified local final_results.json (28 October 2026).",
        ],
    }
    columns, rows = [], []
    for regime, _ in REGIMES:
        reference = pilot["regimes"][regime]["static"]["metrics"]
        for metric, label, direction in zip(METRICS, LABELS, DIRECTIONS, strict=True):
            columns.append(
                {
                    "label": label,
                    "direction": direction,
                    "sample": f"n = {reference[metric]['denominator']:,}",
                }
            )
    for arm, label in ARMS:
        cells = []
        for regime, _ in REGIMES:
            record = pilot["regimes"][regime][arm]
            require(record["planned_queries"] == 216, "Unexpected pilot denominator")
            require(
                record["logical_audit_tickets"] == (40 if arm in {"R", "C", "M", "S"} else 0),
                "Unequal audit accounting",
            )
            for metric in METRICS:
                value = record["metrics"][metric]
                require(
                    value["missing"] == 0 and value["known"] == value["denominator"],
                    "Incomplete pilot metric",
                )
                cells.append(number(value["numerator"], value["denominator"]))
        rows.append({"key": arm, "label": label, "cells": cells})
    second = {
        "stem": "table_2_selective_propagation_pilot",
        "title": "Selective evidence propagation: preliminary subset evaluation",
        "subtitle": "GPT-4o-mini | 256 unique MPBench inputs (8 development groups); "
        "3,888 saved answer events",
        "groups": [
            {"label": label, "start": i * 4, "count": 4} for i, (_, label) in enumerate(REGIMES)
        ],
        "columns": columns,
        "method_width": 252,
        "column_widths": [63] * 12,
        "rows": rows,
        "caption": [
            "<b>Table 2.</b> Rates (%) on three provisional conditions. "
            "Each has 216 probe questions per method; metric denominators appear above. "
            "Utility = combined benign memory-use score, not general QA accuracy.",
            "<b>Bold:</b> best per column including all ties and the no-memory control "
            "(zero retention). R/C/M/S receive identical B = 5 tickets per group "
            "(40 per condition); static/control receive none.",
            "Feedback is AI-simulated and unverified; human validation is pending. "
            "Source-grounded QA is unvalidated/unscored. Distributed/Localized "
            "are strong case-intent overlays, not verified unsafe-memory regimes.",
            "The same 256 inputs are reused; reserved audit cases and probe cohorts can differ. "
            "These are development results, not independent replications "
            "or a confirmed superiority finding.",
            "<b>Our proposed method has NOT been evaluated on the full "
            "6,240-case MPBench dataset.</b>",
            "<i>Source:</i> verified frozen comparison.json, D00-D07 (1 November 2026). "
            "Only methods with saved pilot outcomes are shown; - denotes unavailable results.",
        ],
    }
    for table in [first, second]:
        require(
            MARGIN * 2 + table["method_width"] + sum(table["column_widths"]) == WIDTH,
            "Table width does not fit page",
        )
        mark_best(table)
    sources = [
        "safe-mem_paper.pdf",
        "reports/mpbench_published_targets.json",
        "reports/safemem_full_mpbench/final_results.json",
        "reports/safemem_full_mpbench/RUN_REPORT.md",
        result_path,
        "research_data/development_comparison_report_v1_20261101/RESULTS.md",
        "reports/RESEARCH_AUDIT_20261101_ARTIFACT_CHECKS_V2.json",
        "reports/PROVISIONAL_RESULTS_20261101_DELIVERY.json",
    ]
    return [first, second], {n: sha(REPO / n) for n in sources}


def draw_table(table, out, dpi):
    import pymupdf
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Paragraph

    for name, file in FONTS.items():
        path = FONT_ROOT / file
        require(path.is_file(), f"Required serif font missing: {path}")
        pdfmetrics.registerFont(TTFont("Table-" + name, str(path)))
    pdfmetrics.registerFontFamily(
        "Table-regular",
        normal="Table-regular",
        bold="Table-bold",
        italic="Table-italic",
        boldItalic="Table-bold",
    )
    style = ParagraphStyle(
        "caption",
        fontName="Table-regular",
        fontSize=11.2,
        leading=14.6,
        textColor="black",
        spaceAfter=4,
    )
    captions = [Paragraph(t, style) for t in table["caption"]]
    caption_heights = [p.wrap(WIDTH - 2 * MARGIN, 10000)[1] for p in captions]
    group_h, metric_h, sample_h, row_h = 28, 24, 18, 29
    top = 77
    header_h = group_h + metric_h + sample_h
    bottom = top + header_h + len(table["rows"]) * row_h
    caption_top = bottom + 15
    height = caption_top + sum(caption_heights) + 4 * (len(captions) - 1) + 20
    path = out / (table["stem"] + ".pdf")
    c = canvas.Canvas(
        str(path), pagesize=(WIDTH, height), pageCompression=1, initialFontName="Table-regular"
    )
    c.setTitle(table["title"])
    c.setAuthor("SAFE-Mem research workspace")
    c.setSubject(
        "Verified result table; preliminary scopes and unavailable results are explicitly labeled"
    )
    c.setCreator("Repository result-table renderer (ReportLab)")
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, WIDTH, height, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Table-bold", 18.5)
    c.drawString(MARGIN, height - 32, table["title"])
    c.setFont("Table-regular", 11.8)
    c.drawString(MARGIN, height - 53, table["subtitle"])
    entries = []

    def line(y, x1=MARGIN, x2=WIDTH - MARGIN, width=0.65):
        c.setLineWidth(width)
        c.line(x1, height - y, x2, height - y)

    def centered(text, x, ytop, width, rowheight, font="Table-regular", size=14.5, record=None):
        require(pdfmetrics.stringWidth(text, font, size) <= width - 6, f"Text too wide: {text}")
        c.setFont(font, size)
        c.drawCentredString(x + width / 2, height - (ytop + rowheight / 2) - size * 0.32, text)
        if record is not None:
            entries.append(
                {
                    **record,
                    "text": text,
                    "font": font,
                    "box": [x, ytop, x + width, ytop + rowheight],
                }
            )

    start = MARGIN + table["method_width"]
    xs = [start]
    for width in table["column_widths"]:
        xs.append(xs[-1] + width)
    line(top, width=1.45)
    for group in table["groups"]:
        i, n = group["start"], group["count"]
        centered(group["label"], xs[i], top + 2, xs[i + n] - xs[i], group_h - 4, size=15.2)
        line(top + group_h, xs[i] + 6, xs[i + n] - 6, 0.65)
    c.setFont("Table-regular", 13.5)
    c.drawString(MARGIN + 4, height - (top + group_h + metric_h / 2) - 4.3, "Method")
    for j, column in enumerate(table["columns"]):
        centered(
            column["label"], xs[j], top + group_h, table["column_widths"][j], metric_h, size=12.4
        )
        centered(
            column["sample"],
            xs[j],
            top + group_h + metric_h,
            table["column_widths"][j],
            sample_h,
            size=10.2,
        )
    line(top + header_h, width=0.95)
    for i, row in enumerate(table["rows"]):
        y = top + header_h + i * row_h
        if row["key"] == "S":
            line(y, width=0.75)
        font = "Table-bold" if row["key"] == "S" else "Table-regular"
        require(
            pdfmetrics.stringWidth(row["label"], font, 14.3) <= table["method_width"] - 8,
            "Method label too wide",
        )
        c.setFont(font, 14.3)
        c.drawString(MARGIN + 4, height - (y + row_h / 2) - 14.3 * 0.32, row["label"])
        for j, cell in enumerate(row["cells"]):
            centered(
                cell["display"],
                xs[j],
                y,
                table["column_widths"][j],
                row_h,
                "Table-bold" if cell["best"] else "Table-regular",
                14.5,
                {"row": row["key"], "column": j, "best": cell["best"]},
            )
    line(bottom, width=1.45)
    y = caption_top
    for p, h in zip(captions, caption_heights, strict=True):
        p.drawOn(c, MARGIN, height - y - h)
        y += h + 4
    c.showPage()
    c.save()

    with pymupdf.open(path) as pdf:
        require(len(pdf) == 1 and abs(pdf[0].rect.width - WIDTH) < 0.01, "Invalid PDF page")
        page = pdf[0]
        text = page.get_text()
        require(
            "NOT been evaluated" in text and "↓" in text and "↑" in text, "Missing caption/arrows"
        )
        spans = [
            s
            for b in page.get_text("dict")["blocks"]
            if "lines" in b
            for text_line in b["lines"]
            for s in text_line["spans"]
        ]
        for span in spans:
            x0, y0, x1, y1 = span["bbox"]
            require(
                -0.5 <= x0 <= x1 <= WIDTH + 0.5 and -0.5 <= y0 <= y1 <= height + 0.5,
                "Text extends beyond PDF page",
            )
        for entry in entries:
            rect = pymupdf.Rect(entry["box"])
            matches = [
                s
                for s in spans
                if s["text"].strip() == entry["text"] and rect.contains(pymupdf.Rect(s["bbox"]))
            ]
            require(len(matches) == 1, f"Missing/overlapping value in cell: {entry}")
            bold = "Bold" in matches[0]["font"]
            require(bold == entry["best"], "PDF bold face differs from exact best-value rule")
        for font in page.get_fonts(full=True):
            require(font[2] == "TrueType", "PDF uses an unexpected non-embedded font type")
        for resolution, suffix in [(dpi, ".png"), (140, "_preview.png")]:
            pix = page.get_pixmap(dpi=resolution, colorspace=pymupdf.csRGB, alpha=False)
            pix.save(out / (table["stem"] + suffix))
        png = out / (table["stem"] + ".png")
        require(png.stat().st_size > 10000, "Empty PNG export")
    return {
        "pdf": path.name,
        "png": png.name,
        "pdf_points": [WIDTH, height],
        "dpi": dpi,
        "numeric_or_missing_cells_verified": len(entries),
        "bold_best_including_ties_verified": True,
        "proposed_method_last": True,
        "font_files": {name: sha(FONT_ROOT / file) for name, file in FONTS.items()},
        "pdf_sha256": sha(path),
        "png_sha256": sha(png),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=600)
    args = parser.parse_args()
    require(args.dpi >= 300, "Use at least 300 dpi")
    require(not args.out.exists(), "Refuse to overwrite a prior table export")
    tables, sources = extract_tables()
    args.out.mkdir(parents=True)
    validation = [draw_table(table, args.out, args.dpi) for table in tables]
    require(
        all(sha(REPO / name) == h for name, h in sources.items()), "Source changed during rendering"
    )
    payload = {
        "tables": tables,
        "source_sha256": sources,
        "paper_table_1_pdf_page": 6,
        "model": "GPT-4o-mini",
        "new_model_calls": 0,
        "full_proposed_method_evaluation": False,
        "human_validation": "pending",
    }
    (args.out / "source_data.json").write_text(json.dumps(payload, indent=2) + "\n")
    (args.out / "validation.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "tables": validation,
                "source_files_unchanged": True,
                "tool_versions": {
                    n: importlib.metadata.version(n) for n in ["reportlab", "pymupdf"]
                },
                "generator_sha256": sha(Path(__file__)),
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":

    def denied(*args, **kwargs):
        raise RuntimeError("Result-table generation is offline; network calls are forbidden")

    with (
        patch.object(socket.socket, "connect", denied),
        patch.object(socket.socket, "connect_ex", denied),
        patch.object(socket, "create_connection", denied),
        patch.object(socket, "getaddrinfo", denied),
    ):
        main()
