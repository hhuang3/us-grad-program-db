"""docs/spec/07_snapshots.md §6: normalization of HTML, MHTML and PDF."""

import hashlib
import unicodedata

import pytest

from gradprog.snapshot import normalize as nz
from gradprog.snapshot.normalize import load_rules, mhtml_location, normalize
from helpers import FIXTURES, REPO, make_mhtml, make_pdf

NOISY = (FIXTURES / "snapshot" / "noisy_page.html").read_bytes()


@pytest.fixture
def text():
    return normalize(NOISY, "html")


@pytest.mark.parametrize(
    "noise",
    ["sessionToken", "color: red", "build 2026", "Alpha University Home", "Programs", "Give now banner",
     "We use cookies", "enable JavaScript", "Template text", "Email", "SVG text", "Contentinfo text",
     "Copyright 2026", "utm_source", "v=12345"],
)
def test_noise_removed(text, noise):
    assert noise not in text


def test_body_kept(text):
    lines = text.splitlines()
    assert lines[0] == "Master of Science in Data Science"
    assert "The program takes three semesters." in lines            # whitespace and &nbsp; collapsed
    assert "Apply by the application portal." in lines             # link text kept, href dropped
    assert "Calculus" in lines and "Linear algebra" in lines


def test_table_rows_in_cell_order(text):
    lines = text.splitlines()
    i = lines.index("Round | Deadline")
    assert lines[i + 1:i + 3] == ["Priority | January 15", "Final | March 1"]


@pytest.mark.parametrize(
    "collapsed",
    [
        "Collapsed FAQ answer: GRE is optional.",          # aria-hidden="true"
        "Collapsed panel: TOEFL 100 or IELTS 7.0.",        # hidden attribute
        "Collapsed panel: final deadline May 1.",          # inline display:none
        "Invisible panel: application fee $85.",           # inline visibility:hidden
    ],
)
def test_collapsed_and_hidden_content_is_kept(text, collapsed):
    # 07 §6.2: nothing is removed by visibility; accordions arrive collapsed because JavaScript is not run.
    assert collapsed in text.splitlines()


def test_accordion_headings_are_kept(text):
    lines = text.splitlines()
    assert "Is the GRE required?" in lines and "English requirements" in lines and "Deadlines" in lines


def test_whitespace_and_nfc(text):
    assert text.endswith("\n") and not text.endswith("\n\n")
    assert "" not in text.splitlines()
    assert all(line == line.strip() and "  " not in line for line in text.splitlines())
    assert "\r" not in text and "\u00a0" not in text
    assert text == unicodedata.normalize("NFC", text)
    assert "Café é composed" in text


def test_deterministic(text):
    assert normalize(NOISY, "html") == text
    assert normalize(bytes(NOISY), "html").encode() == text.encode()


def test_charset_from_meta_and_header():
    latin = '<html><head><meta charset="iso-8859-1"></head><body><p>Résumé</p></body></html>'.encode("latin-1")
    assert normalize(latin, "html") == "Résumé\n"
    no_meta = "<html><body><p>Résumé</p></body></html>".encode("latin-1")
    assert normalize(no_meta, "html", charset="iso-8859-1") == "Résumé\n"


def test_undecodable_bytes_do_not_crash():
    assert "\ufffd" in normalize(b"<p>bad \xff byte</p>", "html")


def test_empty_page_normalizes_to_empty():
    assert normalize(b"<html><body><script>render()</script></body></html>", "html") == ""


# --- per-domain rules (§6.3) --------------------------------------------------

def test_domain_rules(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "a.edu:\n  - {remove_selector: 'ul'}\n  - {remove_line_regex: '^Final \\|'}\n", encoding="utf-8")
    rules = load_rules(path)
    with_rules = normalize(NOISY, "html", domain="a.edu", rules=rules)
    assert "Calculus" not in with_rules and "Final | March 1" not in with_rules
    assert "Priority | January 15" in with_rules
    other_domain = normalize(NOISY, "html", domain="b.edu", rules=rules)
    assert "Calculus" in other_domain


def test_rules_file_is_bound_to_normalizer_version():
    # Changing config/normalize_rules.yaml without bumping NORMALIZER_VERSION must fail this test.
    data = (REPO / "config" / "normalize_rules.yaml").read_bytes()
    assert nz.RULES_SHA256[nz.NORMALIZER_VERSION] == hashlib.sha256(data).hexdigest()


def test_initial_rules_are_empty():
    assert load_rules(REPO / "config" / "normalize_rules.yaml") == {}


@pytest.mark.parametrize("bad", ["a.edu: [{drop: 'x'}]\n", "a.edu: [{remove_selector: 'ul', remove_line_regex: 'x'}]\n",
                                 "a.edu: [{remove_line_regex: '('}]\n"])
def test_invalid_rules_rejected(tmp_path, bad):
    path = tmp_path / "rules.yaml"
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(ValueError):
        load_rules(path)


# --- MHTML and PDF ------------------------------------------------------------

def test_mhtml_body_and_location():
    raw = make_mhtml("https://datascience.alpha.edu/ms", NOISY.decode("utf-8"))
    assert mhtml_location(raw) == "https://datascience.alpha.edu/ms"
    assert normalize(raw, "mhtml") == normalize(NOISY, "html")


def test_mhtml_location_falls_back_to_part_header():
    raw = make_mhtml("https://datascience.alpha.edu/ms", "<p>x</p>", snapshot_header=False)
    assert mhtml_location(raw) == "https://datascience.alpha.edu/ms"


def test_mhtml_without_any_location():
    raw = make_mhtml("https://datascience.alpha.edu/ms", "<p>x</p>", snapshot_header=False, part_location=False)
    assert mhtml_location(raw) is None


def test_pdf_text():
    raw = make_pdf(["Application deadline:   January 15", "Tuition per credit: $1,800"])
    assert normalize(raw, "pdf") == "Application deadline: January 15\nTuition per credit: $1,800\n"


def test_unknown_content_type():
    with pytest.raises(ValueError):
        normalize(b"x", "docx")
