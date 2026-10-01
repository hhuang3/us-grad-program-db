"""docs/spec/03_stem_logic.md §1 (normalization) and 01_reference_data.md §2 (CIP 2020)."""

import pandas as pd
import pytest

from gradprog.ref.cip import (
    CipFormatError,
    is_valid_cip2020,
    normalize_cip4,
    normalize_cip6,
    parse_cip2020_csv,
)


# --- normalize_cip6 (03 §1.2) -------------------------------------------------

@pytest.mark.parametrize(
    "value, expected",
    [
        ("03.0204", "03.0204"),      # rule A
        ("3.0204", "03.0204"),       # rule B
        ("030204", "03.0204"),       # rule C
        ("03.0204 ", "03.0204"),     # trailing space
        ("  27.0501\n", "27.0501"),  # surrounding whitespace
        (" 30.7001\t", "30.7001"),  # non-breaking space and tab
        ('="03.0204"', "03.0204"),   # Excel-protected form
        (' ="030204" ', "03.0204"),  # Excel form wrapping rule C, outer spaces
        ("15.0000", "15.0000"),
        (3.0204, "03.0204"),         # float via repr
        (30.7001, "30.7001"),
    ],
)
def test_normalize_cip6_valid(value, expected):
    assert normalize_cip6(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "", "   ", "99", "03.02", "3.02", "27.05", "30204", "03-0204", "03.0204a",
        "03 .0204", "03.02 04", "０３.０２０４", "003.0204", "03.02040", "3.204",
        '="03.02"', "abc",
        27.05,       # float that lost trailing zeros -> ambiguous
        3.02,
    ],
)
def test_normalize_cip6_rejects(value):
    with pytest.raises(CipFormatError) as exc:
        normalize_cip6(value)
    assert repr(value) in str(exc.value)
    assert isinstance(exc.value, ValueError)


@pytest.mark.parametrize("value", [30204, True, None, b"03.0204", ["03.0204"]])
def test_normalize_cip6_rejects_other_types(value):
    with pytest.raises(TypeError):
        normalize_cip6(value)


# --- normalize_cip4 (03 §1.3) -------------------------------------------------

@pytest.mark.parametrize(
    "value, expected",
    [("3070", "30.70"), ("0110", "01.10"), ("30.70", "30.70"), (" 4506 ", "45.06"), ('="2705"', "27.05")],
)
def test_normalize_cip4_valid(value, expected):
    assert normalize_cip4(value) == expected


@pytest.mark.parametrize("value", ["3.70", "370", "30700", "30.7001", "", "30-70"])
def test_normalize_cip4_rejects(value):
    with pytest.raises(CipFormatError):
        normalize_cip4(value)


@pytest.mark.parametrize("value", [3070, 30.70, None])
def test_normalize_cip4_rejects_non_str(value):
    with pytest.raises(TypeError):
        normalize_cip4(value)


# --- CIP 2020 parsing (01 §2) -------------------------------------------------

def test_parse_cip2020_matches_hand_built_reference(fixtures, cip2020):
    parsed = parse_cip2020_csv(fixtures / "cip2020_raw_sample.csv")
    assert list(parsed.columns) == ["cip_code", "level", "title", "definition", "action"]
    got = parsed.astype(str).reset_index(drop=True)
    pd.testing.assert_frame_equal(got, cip2020.astype(str).reset_index(drop=True))


def test_parse_cip2020_drops_moved_from_and_deleted_keeps_moved_to(fixtures):
    parsed = parse_cip2020_csv(fixtures / "cip2020_raw_sample.csv")
    codes = set(parsed["cip_code"])
    assert "51.2502" not in codes      # Moved from
    assert "51.25" not in codes        # Moved from (4-digit)
    assert "45.14" not in codes        # Deleted
    assert "01.8105" in codes          # Moved to = valid new location
    assert set(parsed["action"]) <= {"No substantive changes", "New", "Moved to"}


def test_parse_cip2020_code_format_by_level(fixtures):
    parsed = parse_cip2020_csv(fixtures / "cip2020_raw_sample.csv")
    patterns = {2: r"^\d{2}$", 4: r"^\d{2}\.\d{2}$", 6: r"^\d{2}\.\d{4}$"}
    for level, pattern in patterns.items():
        subset = parsed[parsed["level"].astype(int) == level]
        assert len(subset) > 0
        assert subset["cip_code"].str.match(pattern).all()
    assert parsed["cip_code"].is_unique


def test_parse_cip2020_unknown_action_raises(tmp_path, fixtures):
    raw = (fixtures / "cip2020_raw_sample.csv").read_text(encoding="utf-8")
    bad = raw.replace('="30.7099","New"', '="30.7099","Renamed"')
    path = tmp_path / "bad.csv"
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(ValueError, match="Renamed"):
        parse_cip2020_csv(path)


def test_is_valid_cip2020(cip2020):
    assert is_valid_cip2020("30.7099", cip2020) is True
    assert is_valid_cip2020("01.8105", cip2020) is True   # Moved to
    assert is_valid_cip2020("51.2502", cip2020) is False  # Moved from
    assert is_valid_cip2020("45.1401", cip2020) is False  # never existed
    assert is_valid_cip2020("14.0100", cip2020) is False  # group header, not a 6-digit code
    assert is_valid_cip2020("15.0000", cip2020) is True   # real 6-digit code ending in 0000
