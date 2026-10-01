"""docs/spec/04_candidate_selection.md §1: target CIP config, expansion and existence checks."""

import pytest

from gradprog.ref.targets import TargetCipError, expand_targets, load_target_config
from helpers import REPO

REAL_EXPANSION = {
    "30.7001": "ds", "30.7099": "ds",
    "30.7101": "analytics", "30.7102": "analytics", "30.7103": "analytics",
    "30.7104": "analytics", "30.7199": "analytics",
    "27.0501": "stats", "27.0599": "stats", "27.0601": "stats",
    "52.1301": "mgmt_sci", "52.1302": "mgmt_sci", "52.1304": "mgmt_sci", "52.1399": "mgmt_sci",
    "45.0603": "econ",
}


def write_config(tmp_path, rows):
    path = tmp_path / "target_cip.csv"
    path.write_text("pattern,kind,cip_group,label\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_real_config_schema():
    config = load_target_config(REPO / "config" / "target_cip.csv")
    assert list(config.columns) == ["pattern", "kind", "cip_group", "label"]
    assert set(config["cip_group"]) == {"ds", "analytics", "stats", "mgmt_sci", "econ"}


def test_real_config_expands_on_fixture_cip(targets):
    assert list(targets.columns) == ["cip_code", "cip_group", "label"]
    # Fixture CIP 2020 lacks 27.0502/27.0503; expansion follows whatever CIP 2020 contains.
    assert dict(zip(targets["cip_code"], targets["cip_group"])) == REAL_EXPANSION
    assert targets["cip_code"].is_unique


def test_expansion_keeps_off_list_code_in_scope(targets):
    assert "30.7099" in set(targets["cip_code"])


def test_prefix_expansion_uses_only_valid_six_digit_codes(targets):
    codes = set(targets["cip_code"])
    assert "30.70" not in codes and "52.13" not in codes
    assert all(len(c) == 7 for c in codes)


def test_all_problems_reported_at_once(tmp_path, cip2020):
    path = write_config(tmp_path, [
        "30.70,prefix,ds,ok",
        "45.0699,exact,econ,missing exact",
        "99.99,prefix,stats,empty prefix",
    ])
    with pytest.raises(TargetCipError) as exc:
        expand_targets(load_target_config(path), cip2020, must_exist=["30.7001"])
    msg = str(exc.value)
    assert "45.0699" in msg and "99.99" in msg


def test_must_exist_missing_from_expansion(tmp_path, cip2020):
    path = write_config(tmp_path, ["30.70,prefix,ds,ok"])
    with pytest.raises(TargetCipError, match="30.7102"):
        expand_targets(load_target_config(path), cip2020, must_exist=["30.7001", "30.7102"])


def test_default_must_exist_list(tmp_path, cip2020):
    # Default must-exist codes: 30.7102, 30.7103, 30.7104, 45.0603, 27.0601.
    path = write_config(tmp_path, ["30.71,prefix,analytics,ok", "45.0603,exact,econ,ok"])
    with pytest.raises(TargetCipError, match="27.0601"):
        expand_targets(load_target_config(path), cip2020)


@pytest.mark.parametrize(
    "row",
    [
        "30.70,wildcard,ds,bad kind",
        "30.70,prefix,business,bad group",
        "3070,prefix,ds,bad prefix pattern",
        "30.7001,prefix,ds,six-digit given as prefix",
        "30.70,exact,ds,four-digit given as exact",
    ],
)
def test_invalid_config_rows(tmp_path, cip2020, row):
    path = write_config(tmp_path, [row])
    with pytest.raises(TargetCipError):
        expand_targets(load_target_config(path), cip2020, must_exist=[])


def test_code_in_two_groups_raises(tmp_path, cip2020):
    path = write_config(tmp_path, ["30.70,prefix,ds,a", "30.7001,exact,stats,b"])
    with pytest.raises(TargetCipError, match="30.7001"):
        expand_targets(load_target_config(path), cip2020, must_exist=[])


def test_same_code_twice_in_same_group_is_deduplicated(tmp_path, cip2020):
    path = write_config(tmp_path, ["30.70,prefix,ds,a", "30.7001,exact,ds,b"])
    out = expand_targets(load_target_config(path), cip2020, must_exist=[])
    assert list(out["cip_code"]).count("30.7001") == 1
