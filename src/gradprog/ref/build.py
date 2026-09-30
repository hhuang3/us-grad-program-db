"""Build data/ref/*.csv from the latest registered raw files and record lineage."""

import io
import zipfile
from pathlib import Path

import pandas as pd

from gradprog.util.download import utc_now
from gradprog.util.manifest import raw_path_for, read_manifest, record_derived


def latest_raw(repo, source, url):
    """Path and sha256 of the most recent manifest entry for (source, url)."""
    m = read_manifest(repo / "data" / "manifest" / "manifest.csv")
    rows = m[(m["source"] == source) & (m["url"] == url)]
    if rows.empty:
        raise ValueError(f"no manifest row for {source} {url}; download or register it first")
    row = rows.sort_values("retrieved_at").iloc[-1]
    path = raw_path_for(repo / "data" / "raw", source, url, row["retrieved_at"])
    if not path.is_file():
        raise ValueError(f"raw file missing for manifest row: {path}")
    return path, row["sha256"]


def read_zip_member(zip_path, member):
    with zipfile.ZipFile(zip_path) as z:
        return z.read(member)


def zip_members(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        return z.namelist()


def csv_from_bytes(data):
    return pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False, encoding="utf-8-sig", low_memory=False)


def _format_float(v):
    """Nullable float -> CSV text: '' for null, integral values without '.0'."""
    if pd.isna(v):
        return ""
    return str(int(v)) if float(v).is_integer() else repr(float(v))


def write_table(repo, name, df, input_shas):
    """Write a derived table deterministically (UTF-8, \\n, booleans as true/false) and record lineage."""
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == bool:
            out[col] = out[col].map({True: "true", False: "false"})
        elif str(out[col].dtype) == "Float64":
            out[col] = out[col].map(_format_float).astype(object)
    path = repo / "data" / "ref" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False, lineterminator="\n", encoding="utf-8")
    record_derived(repo / "data" / "manifest" / "derived.csv", path, input_shas, utc_now())
    return path


def build_cip2020(repo):
    from gradprog.ref.cip import parse_cip2020_csv
    from gradprog.ref.sources import DOWNLOADS

    path, sha = latest_raw(repo, "cip2020", DOWNLOADS["cip2020"][0])
    df = parse_cip2020_csv(path)
    write_table(repo, "cip2020.csv", df, [sha])
    return df


def build_stem(repo):
    from gradprog.ref.sources import DOWNLOADS, MANUAL
    from gradprog.ref.stem import extract_pdf_words, parse_stem_words

    cip_path, cip_sha = latest_raw(repo, "cip2020", DOWNLOADS["cip2020"][0])
    pdf_path, pdf_sha = latest_raw(repo, "dhs_stem", MANUAL["dhs_stem"])
    cip2020 = pd.read_csv(repo / "data" / "ref" / "cip2020.csv", dtype=str, keep_default_na=False)
    result = parse_stem_words(extract_pdf_words(pdf_path), cip2020)
    write_table(repo, "stem_list.csv", result.stem_list, [pdf_sha, cip_sha])
    write_table(repo, "stem_core_series.csv", result.core_series, [pdf_sha, cip_sha])
    print(f"stem: last_updated={result.last_updated}, core_series={list(result.core_series['series'])}, "
          f"dropped_group_headers={result.dropped_group_headers}, title_mismatches={len(result.title_mismatches)}")
    return result.stem_list


def _read_ref(repo, name):
    return pd.read_csv(repo / "data" / "ref" / name, dtype=str, keep_default_na=False)


def _targets(repo):
    from gradprog.ref.targets import expand_targets, load_target_config

    return expand_targets(load_target_config(repo / "config" / "target_cip.csv"), _read_ref(repo, "cip2020.csv"))


def _ipeds_inputs(repo):
    from gradprog.ref.ipeds import select_revised_member
    from gradprog.ref.sources import DOWNLOADS

    c_url = next(u for u in DOWNLOADS["ipeds_completions"] if u.endswith("/C2024_A.zip"))
    c_path, c_sha = latest_raw(repo, "ipeds_completions", c_url)
    hd_path, hd_sha = latest_raw(repo, "ipeds_hd", DOWNLOADS["ipeds_hd"][0])
    member = select_revised_member(zip_members(c_path))
    completions = csv_from_bytes(read_zip_member(c_path, member))
    hd_members = [n for n in zip_members(hd_path) if n.lower().endswith(".csv")]
    if len(hd_members) != 1:
        raise ValueError(f"expected one CSV in {hd_path.name}, found {hd_members}")
    hd = csv_from_bytes(read_zip_member(hd_path, hd_members[0]))
    return completions, member, c_sha, hd, hd_sha


def build_ipeds(repo):
    from gradprog.ref.ipeds import build_candidates, build_candidates_by_institution, build_ipeds_masters_target
    from gradprog.ref.sources import DOWNLOADS, IPEDS_DATA_YEAR, MANUAL
    from gradprog.ref.stem import StemReference

    completions, member, c_sha, hd, hd_sha = _ipeds_inputs(repo)
    print(f"ipeds: using {member} ({len(completions):,} rows), HD {len(hd):,} rows")
    cip_sha = latest_raw(repo, "cip2020", DOWNLOADS["cip2020"][0])[1]
    pdf_sha = latest_raw(repo, "dhs_stem", MANUAL["dhs_stem"])[1]
    table = build_ipeds_masters_target(completions, hd, _targets(repo), IPEDS_DATA_YEAR)
    write_table(repo, "ipeds_masters_target_cip.csv", table, [c_sha, hd_sha, cip_sha])
    ref = StemReference.load(repo / "data" / "ref")
    candidates = build_candidates(table, hd, _read_ref(repo, "cip2020.csv"), ref)
    inputs = [c_sha, hd_sha, cip_sha, pdf_sha]
    write_table(repo, "candidates.csv", candidates, inputs)
    by_inst = build_candidates_by_institution(candidates)
    write_table(repo, "candidates_by_institution.csv", by_inst, inputs)
    excluded = table[~table["unitid"].isin(set(candidates["unitid"]))]
    print(f"ipeds: reference {len(table):,} rows / {table['unitid'].nunique()} institutions; "
          f"candidates {len(candidates):,} rows / {by_inst.shape[0]} institutions; "
          f"excluded by state: {excluded['state'].value_counts().to_dict()}")
    return table


def build_scorecard(repo):
    from gradprog.ref.scorecard import build_scorecard_fos_target
    from gradprog.ref.sources import DOWNLOADS

    url = next(u for u in DOWNLOADS["scorecard_fos"] if u.endswith(".zip"))
    path, sha = latest_raw(repo, "scorecard_fos", url)
    members = [n for n in zip_members(path) if n.lower().endswith(".csv")]
    if len(members) != 1:
        raise ValueError(f"expected one CSV in {path.name}, found {members}")
    raw = csv_from_bytes(read_zip_member(path, members[0]))
    cip_sha = latest_raw(repo, "cip2020", DOWNLOADS["cip2020"][0])[1]
    table = build_scorecard_fos_target(raw, _targets(repo), _read_ref(repo, "cip2020.csv"))
    write_table(repo, "scorecard_fos_masters_target.csv", table, [sha, cip_sha])
    no_id = raw[(raw["UNITID"].str.strip() == "NA") & (raw["CREDLEV"].str.strip() == "5")
                & raw["CIPCODE"].str.strip().str[:4].isin({c.replace(".", "") for c in table["cip4"]})]
    print(f"scorecard: {members[0]} {len(raw):,} rows -> {len(table):,} master's rows in target parents; "
          f"excluded UNITID=NA: {int((raw['UNITID'].str.strip() == 'NA').sum()):,} rows overall, "
          f"{len(no_id)} in target parents x master's")
    return table


STEPS = {"cip2020": build_cip2020, "stem": build_stem, "ipeds": build_ipeds, "scorecard": build_scorecard}


def build(repo, only=None):
    repo = Path(repo)
    for name, step in STEPS.items():
        if only and name not in only:
            continue
        df = step(repo)
        print(f"{name}: {len(df):,} rows")
