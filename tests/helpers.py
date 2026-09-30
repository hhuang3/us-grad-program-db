"""Helpers shared by several test modules. Fixtures live in conftest.py."""

from pathlib import Path

import pandas as pd
import yaml

TESTS = Path(__file__).parent
FIXTURES = TESTS / "fixtures"
REPO = TESTS.parent
EXPECTED_COUNTS = REPO / "config" / "expected_counts.yaml"


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
