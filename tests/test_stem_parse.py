"""docs/spec/03_stem_logic.md §3: STEM list PDF structure, tested on a hand-made word layout."""

import copy

import pytest

from gradprog.ref.stem import StemParseError, parse_core_series_from_intro, parse_stem_words
from helpers import pdf_words as words

EXPECTED_CODES = [
    "03.0204", "14.0101", "14.0201", "15.0000", "27.0501", "27.0599",
    "30.7001", "30.7102", "43.0407", "45.0603", "52.1301",
]


@pytest.fixture
def parsed(stem_words, cip2020):
    return parse_stem_words(stem_words, cip2020)


def test_stem_list_columns_and_codes(parsed):
    df = parsed.stem_list
    assert list(df.columns) == ["cip_code", "title", "series", "page"]
    assert list(df["cip_code"]) == EXPECTED_CODES
    assert df["cip_code"].is_unique
    assert df["cip_code"].str.match(r"^\d{2}\.\d{4}$").all()
    assert (df["series"] == df["cip_code"].str[:2]).all()


def test_pages_are_one_based(parsed):
    pages = dict(zip(parsed.stem_list["cip_code"], parsed.stem_list["page"].astype(int)))
    assert pages["03.0204"] == 1
    assert pages["52.1301"] == 2


def test_wrapped_title_joined_from_above_and_below(parsed):
    titles = dict(zip(parsed.stem_list["cip_code"], parsed.stem_list["title"]))
    assert titles["14.0201"] == "Aerospace, Aeronautical, and Astronautical/Space Engineering, General."


def test_irregular_spacing_collapsed_to_single_space(parsed):
    titles = dict(zip(parsed.stem_list["cip_code"], parsed.stem_list["title"]))
    assert titles["30.7102"] == "Business Analytics."


def test_split_code_fragments_are_joined(parsed):
    titles = dict(zip(parsed.stem_list["cip_code"], parsed.stem_list["title"]))
    assert titles["43.0407"] == "Geospatial Intelligence."


def test_real_code_ending_in_0000_is_kept(parsed):
    assert "15.0000" in set(parsed.stem_list["cip_code"])


def test_series_headers_go_to_core_series(parsed):
    core = parsed.core_series
    assert list(core.columns) == ["series", "title", "page"]
    assert list(core["series"]) == ["14", "27"]
    assert list(core["title"]) == ["ENGINEERING.", "MATHEMATICS AND STATISTICS."]


def test_four_digit_group_headers_dropped_and_counted(parsed):
    codes = set(parsed.stem_list["cip_code"])
    assert "14.0100" not in codes and "27.0500" not in codes
    assert "14.0000" not in codes and "27.0000" not in codes
    assert parsed.dropped_group_headers == 2


def test_last_updated_is_iso_date(parsed):
    assert parsed.last_updated == "2024-07-22"


def test_title_kept_as_in_pdf_and_mismatch_reported(parsed):
    titles = dict(zip(parsed.stem_list["cip_code"], parsed.stem_list["title"]))
    assert titles["03.0204"] == "Environmental/Natural Resources Economics."
    assert parsed.title_mismatches == ["03.0204"]


def test_intro_text_above_table_is_not_parsed_as_rows(parsed):
    # Intro words extend past x=205 but sit above the table header.
    assert all(" CIP series " not in t for t in parsed.stem_list["title"])


# --- failure modes (03 §3.2–3.4) ----------------------------------------------

def test_series_column_must_match_code_prefix(stem_words, cip2020):
    pages = copy.deepcopy(stem_words)
    for w in pages[1]:
        if w["text"] == "27" and w["top"] == 317:
            w["text"] = "26"
    with pytest.raises(StemParseError):
        parse_stem_words(pages, cip2020)


def test_code_not_in_cip2020_raises(stem_words, cip2020):
    pages = copy.deepcopy(stem_words)
    pages[1] += words("99", 79, 429) + words("99.9999", 144, 429) + words("Made Up.", 216, 429)
    with pytest.raises(StemParseError, match="99.9999"):
        parse_stem_words(pages, cip2020)


def test_duplicate_code_raises(stem_words, cip2020):
    pages = copy.deepcopy(stem_words)
    pages[1] += words("52", 79, 429) + words("52.1301", 144, 429) + words("Management Science.", 216, 429)
    with pytest.raises(StemParseError, match="52.1301"):
        parse_stem_words(pages, cip2020)


def test_equidistant_title_fragment_raises(stem_words, cip2020):
    pages = copy.deepcopy(stem_words)
    pages[0] += words("Orphan", 216, 293)  # exactly between rows at 285 and 301
    with pytest.raises(StemParseError):
        parse_stem_words(pages, cip2020)


def test_inconsistent_last_updated_raises(stem_words, cip2020):
    pages = copy.deepcopy(stem_words)
    for w in pages[1]:
        if w["text"] == "23," or (w["text"] == "22," and w["top"] == 740):
            w["text"] = "23,"
    with pytest.raises(StemParseError):
        parse_stem_words(pages, cip2020)


def test_missing_footer_raises(stem_words, cip2020):
    pages = copy.deepcopy(stem_words)
    pages[1] = [w for w in pages[1] if w["top"] != 740]
    with pytest.raises(StemParseError):
        parse_stem_words(pages, cip2020)


def test_missing_table_header_raises(stem_words, cip2020):
    pages = copy.deepcopy(stem_words)
    pages[1] = [w for w in pages[1] if w["text"] != "Series"]
    with pytest.raises(StemParseError):
        parse_stem_words(pages, cip2020)


def test_title_fragment_on_page_without_code_rows_raises(stem_words, cip2020):
    pages = copy.deepcopy(stem_words)
    page3 = [w for w in pages[1] if w["top"] < 285 or w["top"] == 740]
    page3 += words("Stray title text.", 216, 300)
    pages.append(page3)
    with pytest.raises(StemParseError):
        parse_stem_words(pages, cip2020)


def test_intro_series_must_equal_header_series(stem_words, cip2020):
    pages = copy.deepcopy(stem_words)
    for w in pages[0]:
        if w["text"] == "(27)." and w["top"] < 200:
            w["text"] = "(26)."
    with pytest.raises(StemParseError):
        parse_stem_words(pages, cip2020)


# --- intro sentence (03 §3.4) -------------------------------------------------

def test_parse_core_series_from_intro_real_like_text():
    text = (
        "Accordingly, this list designates the following four primary CIP series at the 2-digit CIP code "
        "level: Engineering (14), Biological and Biomedical Sciences (26), Mathematics and Statistics (27) "
        "and Physical Sciences (40). Any new additions to those areas will automatically be included on "
        "this STEM Designated Degree Program List. This list also includes CIPs from the following 18 "
        "related CIP series at the 6-digit CIP code level: Agricultural (01); Natural Resources (03)."
    )
    assert parse_core_series_from_intro(text) == {"14", "26", "27", "40"}


def test_parse_core_series_from_intro_missing_anchor_raises():
    with pytest.raises(StemParseError):
        parse_core_series_from_intro("Engineering (14) and Physical Sciences (40).")


# --- layout-change guards (03 §3.5) -------------------------------------------

def test_series_without_code_raises(stem_words, cip2020):
    pages = copy.deepcopy(stem_words)
    pages[1] += words("30", 79, 429)
    with pytest.raises(StemParseError):
        parse_stem_words(pages, cip2020)


def test_text_in_code_column_raises(stem_words, cip2020):
    pages = copy.deepcopy(stem_words)
    pages[1] += words("see note", 150, 429)
    with pytest.raises(StemParseError):
        parse_stem_words(pages, cip2020)


def test_code_in_title_column_raises(stem_words, cip2020):
    # e.g. columns shifted right: a code lands where titles are expected
    pages = copy.deepcopy(stem_words)
    pages[1] += words("52", 79, 429) + words("52.1302", 216, 429)
    with pytest.raises(StemParseError):
        parse_stem_words(pages, cip2020)


def test_code_outside_table_region_raises(stem_words, cip2020):
    # a row below the footer would otherwise be silently dropped
    pages = copy.deepcopy(stem_words)
    pages[1] += words("52", 79, 760) + words("52.1302", 144, 760) + words("Business Statistics.", 216, 760)
    with pytest.raises(StemParseError, match="52.1302"):
        parse_stem_words(pages, cip2020)


def test_code_in_intro_area_raises(stem_words, cip2020):
    pages = copy.deepcopy(stem_words)
    pages[0] += words("See 30.7001 below.", 72, 195)
    with pytest.raises(StemParseError, match="30.7001"):
        parse_stem_words(pages, cip2020)
