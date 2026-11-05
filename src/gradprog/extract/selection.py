"""Which page × program pairs are extracted in a run (08 §2, §2.1, §11)."""

from dataclasses import asdict, dataclass

from gradprog.snapshot.normalize import NORMALIZER_VERSION
from gradprog.snapshot.store import SUCCESS

FAILED_CALLS = ("api_error", "refusal", "max_tokens")   # 08 §2.1: these do not count as an extraction
EXTRACTED = ("ok", "invalid_output")
MAX_CALL_FAILURES = 2


@dataclass(frozen=True)
class Call:
    action: str          # call, unavailable, skip, needs_review, no_snapshot
    page_id: str
    program_id: str
    snapshot_id: str = ""
    norm_sha256: str = ""
    norm_chars: int = 0
    normalizer_version: str = ""
    classification: str = ""
    retrieved_at: str = ""
    final_url: str = ""
    page_url: str = ""
    page_type: str = ""
    owner_level: str = ""
    scope_note: str = ""
    program_name: str = ""
    degree_type: str = ""
    intake_terms: str = ""
    prior_failures: int = 0

    def to_dict(self):
        return asdict(self)


def _latest_rows(index):
    """Per page: rows oldest first, one per snapshot. A renormalized snapshot keeps its place in time."""
    current = index[index["normalizer_version"].isin(["", str(NORMALIZER_VERSION)])]
    return current.sort_values("retrieved_at", kind="stable").drop_duplicates("snapshot_id", keep="last")


def _records_for(records, page_id, program_id):
    return [r for r in records if r["page_id"] == page_id and r["program_id"] == program_id]


def _same_inputs(record, sha, versions):
    return (record["norm_sha256"] == sha and all(str(record[k]) == str(v) for k, v in versions.items()))


def _failures_since_extraction(records, sha, versions):
    """Consecutive failed calls on these inputs; a success or new inputs start the count again (08 §2.1)."""
    count = 0
    for record in reversed(records):
        if record["status"] == "page_unavailable":
            continue
        if record["status"] not in FAILED_CALLS or not _same_inputs(record, sha, versions):
            break
        count += 1
    return count


def plan_calls(registry, index, records, versions, pages=None, retry_failed=False):
    """One Call per selected program × confirmed page; `versions` holds prompt_version, schema_version, model_name."""
    programs = registry.programs[registry.programs["status"] == "selected"].set_index("program_id")
    page_table = registry.pages.drop_duplicates("page_id").set_index("page_id")
    rows = _latest_rows(index)
    out = []
    for link in registry.program_pages.sort_values(["page_id", "program_id"]).itertuples():
        if link.program_id not in programs.index or link.page_id not in page_table.index:
            continue
        page = page_table.loc[link.page_id]
        if page["url_status"] != "confirmed" or (pages and link.page_id not in pages):
            continue
        program = programs.loc[link.program_id]
        base = dict(page_id=link.page_id, program_id=link.program_id, page_url=page["url"], page_type=page["page_type"],
                    owner_level=page["owner_level"], scope_note=link.scope_note, program_name=program["program_name"],
                    degree_type=program["degree_type"], intake_terms=program["intake_terms"])
        out.append(_plan_one(base, rows[rows["page_id"] == link.page_id], records, versions, retry_failed))
    return out


def _plan_one(base, page_rows, records, versions, retry_failed):
    if page_rows.empty:
        return Call("no_snapshot", **base)
    mine = _records_for(records, base["page_id"], base["program_id"])
    latest = page_rows.iloc[-1]
    if latest["classification"] not in SUCCESS:
        done = any(r["snapshot_id"] == latest["snapshot_id"] and r["status"] == "page_unavailable" for r in mine)
        return Call("skip" if done else "unavailable", snapshot_id=latest["snapshot_id"],
                    classification=latest["classification"], retrieved_at=latest["retrieved_at"], **base)
    fields = dict(snapshot_id=latest["snapshot_id"], norm_sha256=latest["norm_sha256"],
                  norm_chars=int(latest["norm_chars"] or 0), normalizer_version=latest["normalizer_version"],
                  classification=latest["classification"], retrieved_at=latest["retrieved_at"],
                  final_url=latest["final_url"], **base)
    extracted = [r for r in mine if r["status"] in EXTRACTED]
    if extracted and _same_inputs(extracted[-1], latest["norm_sha256"], versions):
        return Call("skip", **fields)
    failures = _failures_since_extraction(mine, latest["norm_sha256"], versions)
    if failures >= MAX_CALL_FAILURES and not retry_failed:
        return Call("needs_review", prior_failures=failures, **fields)
    return Call("call", prior_failures=failures, **fields)
