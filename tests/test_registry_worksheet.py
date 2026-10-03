"""docs/spec/06_source_registry.md §2.4 and §7: selection worksheet."""

import pytest

from gradprog.registry.tables import RegistryError
from gradprog.registry.worksheet import build_worksheet, write_worksheet

COLUMNS = [
    "cip_group", "worksheet_rank", "unitid", "institution_name", "state", "cip_code", "cip_title", "on_stem_list",
    "completions_masters_nonresident", "completions_masters", "institution_group_count", "decision", "note",
]


@pytest.fixture
def ws(registry_candidates):
    return build_worksheet(registry_candidates)


def test_columns(ws):
    assert list(ws.columns) == COLUMNS


def test_one_row_per_candidate(ws, registry_candidates):
    assert len(ws) == len(registry_candidates)


def test_order_nonresident_then_total_then_unitid(ws):
    ds = ws[ws["cip_group"] == "ds"]
    assert list(ds["unitid"]) == ["200002", "200007", "200006", "200001", "200005"]
    assert list(ds["worksheet_rank"].astype(int)) == [1, 2, 3, 4, 5]


def test_groups_in_fixed_order(ws):
    order = list(dict.fromkeys(ws["cip_group"]))
    assert order == ["ds", "analytics", "stats", "mgmt_sci", "econ"]


def test_rank_restarts_per_group(ws):
    firsts = ws.groupby("cip_group", sort=False)["worksheet_rank"].first().astype(int)
    assert set(firsts) == {1}


def test_institution_group_count(ws):
    counts = dict(zip(ws["unitid"], ws["institution_group_count"].astype(int)))
    assert counts["200001"] == 2 and counts["200004"] == 2 and counts["200002"] == 1


def test_decision_and_note_are_blank(ws):
    assert set(ws["decision"]) == {""} and set(ws["note"]) == {""}


def test_write_is_deterministic_and_refuses_overwrite(ws, tmp_path):
    path = tmp_path / "selection_worksheet.csv"
    write_worksheet(ws, path)
    first = path.read_bytes()
    with pytest.raises(RegistryError):
        write_worksheet(ws, path)
    write_worksheet(ws, path, force=True)
    assert path.read_bytes() == first
    assert first.startswith(",".join(COLUMNS).encode() + b"\n")
