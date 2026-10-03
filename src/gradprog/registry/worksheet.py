"""Selection worksheet (06 §7)."""

from pathlib import Path

from gradprog.ref.targets import GROUP_ORDER
from gradprog.registry.tables import RegistryError

COLUMNS = [
    "cip_group", "worksheet_rank", "unitid", "institution_name", "state", "cip_code", "cip_title", "on_stem_list",
    "completions_masters_nonresident", "completions_masters", "institution_group_count", "decision", "note",
]


def build_worksheet(candidates):
    ws = candidates.copy()
    ws["_g"] = ws["cip_group"].map({g: i for i, g in enumerate(GROUP_ORDER)})
    ws["_nr"] = ws["completions_masters_nonresident"].astype(int)
    ws["_n"] = ws["completions_masters"].astype(int)
    ws["_u"] = ws["unitid"].astype(int)
    ws = ws.sort_values(["_g", "_nr", "_n", "_u", "cip_code"], ascending=[True, False, False, True, True])
    ws["worksheet_rank"] = ws.groupby("cip_group").cumcount() + 1
    ws["institution_group_count"] = ws.groupby("unitid")["cip_group"].transform("nunique")
    ws["decision"] = ""
    ws["note"] = ""
    return ws[COLUMNS].reset_index(drop=True)


def write_worksheet(worksheet, path, force=False):
    path = Path(path)
    if path.exists() and not force:
        raise RegistryError(f"{path} already exists (it may contain your decisions); use --force to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    worksheet.to_csv(path, index=False, lineterminator="\n", encoding="utf-8")
