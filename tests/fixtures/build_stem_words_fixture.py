"""Build tests/fixtures/stem_pdf_words.json: a hand-made imitation of the word
layout pdfplumber extracts from the DHS STEM list PDF (docs/spec/03_stem_logic.md §3).

Coordinates mimic the real 2024 PDF: series column x0=79, code x0=144, title x0=216.
Content is a tiny made-up subset, not a copy of the PDF.

Run: uv run python tests/fixtures/build_stem_words_fixture.py
"""

import json
from pathlib import Path

OUT = Path(__file__).with_name("stem_pdf_words.json")


def phrase(text, x, top):
    words = []
    for token in text.split():
        width = 5.5 * len(token)
        words.append({"text": token, "x0": x, "x1": x + width, "top": top, "bottom": top + 10})
        x += width + 2.5
    return words


def page_header():
    return (
        phrase("Homeland Security Investigations", 72, 40)
        + phrase("National Security Division", 72, 52)
        + phrase("Student and Exchange Visitor Program", 72, 64)
    )


def table_header():
    return (
        phrase("CIP Code", 84, 210)
        + phrase("2020 CIP", 152, 224)
        + phrase("Two-Digit", 81, 236)
        + phrase("CIP Code Title", 345, 236)
        + phrase("Code", 162, 248)
        + phrase("Series", 91, 260)
    )


def footer(page_no, date="July 22, 2024"):
    return phrase(f"Last updated: {date}", 72, 740) + phrase(f"{page_no} | P a g e", 484, 740)


def row(series, code, title, top):
    words = phrase(series, 79, top) + phrase(code, 144, top)
    if title:
        words += phrase(title, 216, top)
    return words


def page1():
    w = page_header()
    w += phrase("DHS STEM Designated Degree Program List", 140, 90)
    w += phrase("Last Updated: July 22, 2024", 228, 104)
    intro = [
        "Accordingly, this list designates the following primary CIP series at the",
        "2-digit CIP code level: Engineering (14) and Mathematics and Statistics (27). Any",
        "new additions to those areas will automatically be included on this list.",
        "This list also includes CIPs from the following related CIP series at the 6-digit",
        "CIP code level: Natural Resources and Conservation (03); Multi/Interdisciplinary Studies (30).",
    ]
    for i, line in enumerate(intro):
        w += phrase(line, 72, 130 + 14 * i)
    w += table_header()
    w += row("03", "03.0204", "Environmental/Natural Resources Economics.", 285)
    w += row("14", "14.0000", "ENGINEERING.", 301)
    w += row("14", "14.0100", "Engineering, General.", 317)
    w += row("14", "14.0101", "Engineering, General.", 333)
    # Wrapped title: first part above the code line, second part below it.
    w += phrase("Aerospace, Aeronautical, and Astronautical/Space Engineering,", 216, 345)
    w += row("14", "14.0201", None, 353)
    w += phrase("General.", 216, 361)
    w += row("15", "15.0000", "Engineering Technologies/Technicians, General.", 377)
    w += footer(1)
    return w


def page2():
    w = page_header() + table_header()
    w += row("27", "27.0000", "MATHEMATICS AND STATISTICS.", 285)
    w += row("27", "27.0500", "Statistics.", 301)
    w += row("27", "27.0501", "Statistics, General.", 317)
    w += row("27", "27.0599", "Statistics, Other.", 333)
    w += row("30", "30.7001", "Data Science, General.", 349)
    # Irregular spacing between title words.
    w += row("30", "30.7102", None, 365) + phrase("Business", 216, 365) + phrase("Analytics.", 290, 365)
    # Code split into several fragments ("43 . 0407").
    w += phrase("43", 79, 381) + phrase("43", 144, 381) + phrase(".", 156, 381) + phrase("0407", 158, 381)
    w += phrase("Geospatial Intelligence.", 216, 381)
    w += row("45", "45.0603", "Econometrics and Quantitative Economics.", 397)
    w += row("52", "52.1301", "Management Science.", 413)
    w += footer(2)
    return w


if __name__ == "__main__":
    OUT.write_text(json.dumps([page1(), page2()], indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
