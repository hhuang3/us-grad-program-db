"""docs/spec/03_stem_logic.md §4 (cip_on_stem_list) and §5 (stem_status)."""

import pytest

from gradprog.ref.cip import CipFormatError, UnknownCipError
from gradprog.ref.stem import (
    cip_on_stem_list,
    cip_on_stem_list_exact,
    derive_stem_status,
    expansion_only_codes,
)


# --- cip_on_stem_list (§4.1) --------------------------------------------------

@pytest.mark.parametrize("code", ["30.7001", "30.7102", "45.0603", "52.1301", "03.0204", "15.0000"])
def test_on_list_by_exact_six_digit_match(stem_ref, code):
    assert cip_on_stem_list(code, stem_ref) is True


@pytest.mark.parametrize("code", ["30.7099", "45.0601", "52.1201"])
def test_valid_cip_not_on_list(stem_ref, code):
    assert cip_on_stem_list(code, stem_ref) is False


def test_input_is_normalized_first(stem_ref):
    assert cip_on_stem_list("307001", stem_ref) is True
    assert cip_on_stem_list(" 3.0204", stem_ref) is True


def test_series_expansion_covers_unlisted_core_series_code(stem_ref):
    # 27.0601 is a valid CIP 2020 code in core series 27 but not enumerated in the fixture list.
    assert cip_on_stem_list("27.0601", stem_ref) is True
    assert cip_on_stem_list_exact("27.0601", stem_ref) is False


def test_series_expansion_only_for_core_series(stem_ref):
    # Series 30 and 45 are related series: six-digit matching only.
    assert cip_on_stem_list("30.7099", stem_ref) is False
    assert cip_on_stem_list("45.0601", stem_ref) is False


def test_malformed_code_raises_format_error(stem_ref):
    with pytest.raises(CipFormatError):
        cip_on_stem_list("30.70", stem_ref)


@pytest.mark.parametrize("code", ["27.0602", "14.0100", "51.2502"])
def test_code_not_in_cip2020_raises_unknown(stem_ref, code):
    # 27.0602 would be in a core series but does not exist; not-existing != not-on-list.
    with pytest.raises(ValueError) as exc:
        cip_on_stem_list(code, stem_ref)
    assert isinstance(exc.value, UnknownCipError)


# --- expansion sentinel on fixtures (§4.3) ------------------------------------

def test_expansion_only_codes_lists_codes_true_only_via_expansion(stem_ref):
    assert expansion_only_codes(stem_ref) == ["27.0601"]


def test_exact_matches_full_rule_for_everything_else(stem_ref, cip2020):
    six = cip2020[cip2020["level"].astype(int) == 6]["cip_code"]
    for code in six:
        if code == "27.0601":
            continue
        assert cip_on_stem_list(code, stem_ref) == cip_on_stem_list_exact(code, stem_ref), code


# --- derive_stem_status: full truth table (§5.2) ------------------------------

ON = "30.7001"   # on list
OFF = "30.7099"  # valid, not on list


@pytest.mark.parametrize(
    "row, cip_source, cip_code, expected",
    [
        (4, "school_stem_page", ON, "confirmed_by_school"),
        (5, "school_stem_page", OFF, "not_on_list"),
        (6, "program_page", ON, "confirmed_by_school"),
        (7, "program_page", OFF, "not_on_list"),
        (8, "i20_statement", ON, "confirmed_by_school"),
        (9, "i20_statement", OFF, "not_on_list"),
        (10, "ipeds_inferred", ON, "cip_on_list_unconfirmed"),
        (11, "ipeds_inferred", OFF, "cip_not_on_list_unconfirmed"),
        (12, "unknown", ON, "cip_on_list_unconfirmed"),
        (13, "unknown", OFF, "cip_not_on_list_unconfirmed"),
        (14, "unknown", None, "unknown"),
        (14, "unknown", "", "unknown"),
        (14, "unknown", "   ", "unknown"),
    ],
)
def test_stem_status_truth_table(stem_ref, row, cip_source, cip_code, expected):
    assert derive_stem_status(cip_code, cip_source, stem_ref) == expected


def test_stem_status_expansion_code_counts_as_on_list(stem_ref):
    assert derive_stem_status("27.0601", "program_page", stem_ref) == "confirmed_by_school"


@pytest.mark.parametrize("cip_source", ["school_stem_page", "program_page", "i20_statement", "ipeds_inferred"])
@pytest.mark.parametrize("cip_code", [None, "", "  "])
def test_stem_status_row15_source_without_code_raises(stem_ref, cip_source, cip_code):
    with pytest.raises(ValueError):
        derive_stem_status(cip_code, cip_source, stem_ref)


@pytest.mark.parametrize("cip_source", [None, "", "school", "IPEDS_INFERRED", "not_mentioned"])
def test_stem_status_row1_invalid_source_raises(stem_ref, cip_source):
    with pytest.raises(ValueError):
        derive_stem_status(ON, cip_source, stem_ref)


def test_stem_status_row2_malformed_code_raises(stem_ref):
    with pytest.raises(CipFormatError):
        derive_stem_status("30.70", "program_page", stem_ref)


def test_stem_status_row3_unknown_code_raises(stem_ref):
    with pytest.raises(UnknownCipError):
        derive_stem_status("27.0602", "ipeds_inferred", stem_ref)


def test_stem_status_never_confirms_without_school_declaration(stem_ref, cip2020):
    six = cip2020[cip2020["level"].astype(int) == 6]["cip_code"]
    for code in six:
        for source in ("ipeds_inferred", "unknown"):
            assert derive_stem_status(code, source, stem_ref) not in {"confirmed_by_school", "not_on_list"}
