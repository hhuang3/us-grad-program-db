"""Helpers shared by several test modules. Fixtures live in conftest.py."""

from pathlib import Path

import pandas as pd
import yaml

TESTS = Path(__file__).parent
FIXTURES = TESTS / "fixtures"
REPO = TESTS.parent
EXPECTED_COUNTS = REPO / "config" / "expected_counts.yaml"
REGISTRY_FIXTURES = FIXTURES / "registry"
REGISTRY_TABLES = ["programs.csv", "pages.csv", "program_pages.csv", "domains.csv"]


def read_str_csv(path):
    """Read a CSV with every column as str and no NA conversion (keeps leading zeros, 'NA', 'PS')."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def pdf_words(text, x, top):
    """Split text into pdfplumber-style word dicts starting at x on one baseline."""
    out = []
    for token in text.split():
        width = 5.5 * len(token)
        out.append({"text": token, "x0": x, "x1": x + width, "top": top, "bottom": top + 10})
        x += width + 2.5
    return out


def load_expected():
    return yaml.safe_load(EXPECTED_COUNTS.read_text(encoding="utf-8"))


def assert_expected(key, actual):
    """Compare a real-data value with config/expected_counts.yaml (dotted key, e.g. 'stem_list.six_digit_codes')."""
    expected = load_expected()
    for part in key.split("."):
        expected = expected[part]
    assert actual == expected, (
        f"[expected_counts] {key}: expected {expected!r}, got {actual!r}.\n"
        "可能是官方数据更新（STEM 清单 / CIP / IPEDS / Scorecard 发布了新版本），"
        "请人工确认后修改 config/expected_counts.yaml；"
        "如果官方数据没有变化，则是代码 bug。"
    )


def copy_registry(dest):
    """Copy the hand-made valid registry fixture into dest and return dest."""
    import shutil

    dest.mkdir(parents=True, exist_ok=True)
    for name in REGISTRY_TABLES:
        shutil.copy(REGISTRY_FIXTURES / name, dest / name)
    return dest


def make_pdf(lines):
    """A minimal one-page PDF (Helvetica) showing the given text lines; built by hand, no dependencies."""
    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    ops = ["BT", "/F1 12 Tf", "72 720 Td"]
    for i, line in enumerate(lines):
        if i:
            ops.append("0 -16 Td")
        ops.append(f"({esc(line)}) Tj")
    ops.append("ET")
    stream = "\n".join(ops).encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def make_mhtml(location, html, snapshot_header=True, part_location=True):
    """A Chrome-style single-file web page (multipart/related, quoted-printable HTML part)."""
    import quopri

    boundary = "----MultipartBoundary--fixture0123456789"
    head = ["From: <Saved by Blink>"]
    if snapshot_header:
        head.append(f"Snapshot-Content-Location: {location}")
    head += ["Subject: Fixture page", "Date: Sat, 3 Oct 2026 12:00:00 -0000", "MIME-Version: 1.0",
             f'Content-Type: multipart/related; type="text/html"; boundary="{boundary}"', "", ""]
    part = [f"--{boundary}", "Content-Type: text/html", "Content-ID: <frame-0@mhtml.blink>",
            "Content-Transfer-Encoding: quoted-printable"]
    if part_location:
        part.append(f"Content-Location: {location}")
    body = quopri.encodestring(html.encode("utf-8")).decode("ascii")
    css = [f"--{boundary}", "Content-Type: text/css", "Content-Transfer-Encoding: quoted-printable",
           "Content-Location: https://example.edu/style.css", "", "body { color: black; }", ""]
    text = "\r\n".join(head) + "\r\n".join(part) + "\r\n\r\n" + body.replace("\n", "\r\n") + "\r\n" \
        + "\r\n".join(css) + f"\r\n--{boundary}--\r\n"
    return text.encode("ascii")
