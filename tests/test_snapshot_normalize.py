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


def test_v2_rules_cover_the_recurring_noise():
    """07 §6.5: the v2 rules file has the domains decided in Phase 3e."""
    rules = load_rules()
    assert nz.NORMALIZER_VERSION == 2
    assert {"infosystems.utdallas.edu", "www.fuqua.duke.edu", "olin.washu.edu", "datascience.virginia.edu",
            "gsas.nyu.edu", "stat.illinois.edu"} <= set(rules)
    duke = [r.get("remove_selector") for r in rules["www.fuqua.duke.edu"]]
    assert ".field--name-field-deadline-date-timer-2" in duke


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



# --- normalizer v2 (07 §6.5) ---------------------------------------------------

def html(body):
    return f"<html><body>{body}</body></html>".encode()


def test_doctype_inside_the_body_is_not_text():
    raw = b"<br/><div>x</div>\n<!DOCTYPE html>\n<html><head><title>T</title></head><body><p>Real text</p></body></html>"
    assert normalize(raw, "html").splitlines()[0] != "html"
    assert "Real text" in normalize(raw, "html")


def test_table_trailing_empty_cells_and_empty_rows():
    t = normalize(html("<table><tr><th>Program</th><th>Fall</th><th>Spring</th><th></th></tr>"
                       "<tr><td>Statistics</td><td>5/6/2027</td><td></td></tr>"
                       "<tr><td>Religion</td><td></td><td>10/29/2026</td></tr>"
                       "<tr><td> </td><td></td></tr></table>"), "html")
    assert t.splitlines() == ["Program | Fall | Spring", "Statistics | 5/6/2027", "Religion | | 10/29/2026"]


DUKE_COUNTDOWN = html(
    '<div class="paragraphs-item-deadline-module">'
    '<h3 class="field--name-field-icon-title"><div>MQM: BA Application Round 2 Deadline</div></h3>'
    '<div class="field--name-field-deadline-date-timer-2"><div>2 months 3 weeks</div></div>'
    '<div class="field--name-field-start-date"><div>Wed, 10/07/2026 - 00:00</div></div>'
    '<div class="field--name-field-end-date"><div>Wed, 01/06/2027 - 23:59</div></div></div>'
    '<div class="field__item"><div class="hidden field__item">Photo Box II - Ask a Student - 2018</div><p>Body</p></div>')


def test_duke_countdown_keeps_round_and_dates():
    t = normalize(DUKE_COUNTDOWN, "html", domain="www.fuqua.duke.edu", rules=load_rules()).splitlines()
    assert "MQM: BA Application Round 2 Deadline" in t
    assert "Wed, 10/07/2026 - 00:00" in t and "Wed, 01/06/2027 - 23:59" in t
    assert "2 months 3 weeks" not in t and not any("Photo Box" in x for x in t)
    assert "Body" in t


def test_domain_rules_do_not_apply_elsewhere():
    t = normalize(DUKE_COUNTDOWN, "html", domain="www.example.edu", rules=load_rules())
    assert "2 months 3 weeks" in t and "Photo Box II - Ask a Student - 2018" in t


def test_nyu_last_updated_line_only_on_gsas():
    raw = html("<p>Apply by January 4.</p><p>Last updated October 2026.</p>")
    assert "Last updated October 2026." not in normalize(raw, "html", domain="gsas.nyu.edu", rules=load_rules())
    assert "Last updated October 2026." in normalize(raw, "html", domain="cds.nyu.edu", rules=load_rules())


# --- protection: data-like lines removed by domain rules (07 §6.5) -------------

def test_rule_losses_counts_data_like_lines_only():
    rules = {"a.edu": [{"remove_selector": ".events"}, {"remove_line_regex": "^Note"}]}
    raw = html('<div class="events"><p>Info session</p><p>October 22, 2026</p><p>Tuition waiver talk</p>'
               '<p>Campus tour</p></div><p>Note: TOEFL 100 required</p><p>Keep me</p>')
    lost = nz.rule_losses(raw, "html", "a.edu", rules)
    assert sorted(lost) == ["Note: TOEFL 100 required", "October 22, 2026", "Tuition waiver talk"]
    assert nz.rule_losses(raw, "html", "b.edu", rules) == []                     # no rules for this domain


@pytest.mark.parametrize("line", ["Deadline: soon", "Apply by the portal", "$75 application fee", "IELTS 7",
                                  "GRE optional", "GMAT", "Duolingo 120", "10/07/2026", "2026-10-07",
                                  "Oct. 7, 2026", "minimum score of 90"])
def test_data_like_patterns(line):
    assert nz.DATA_LIKE.search(line)


@pytest.mark.parametrize("line", ["Campus tour", "Meet our students", "Class of 2024"])
def test_not_data_like(line):
    assert not nz.DATA_LIKE.search(line)