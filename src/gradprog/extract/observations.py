"""Turn one call's LLM output into observation rows (08 §4, §4.1, §6, §7, §9). No files, no LLM."""

import hashlib
from datetime import date

from gradprog.extract.conflicts import in_page_conflicts
from gradprog.extract.derive import cip_source, stem_status
from gradprog.extract.evidence import check_entry, toefl_scale
from gradprog.extract.fields import ALL_FIELDS, GROUPS, OBSERVATION_FIELDS
from gradprog.extract.prompt import EXTRACT_RULES_VERSION
from gradprog.extract.terms import academic_year_as_written, deadline_term, tuition_term, undated_term

TOEFL_FIELDS = {"legacy": "toefl_min_legacy", "new": "toefl_min_new_scale"}
TUITION_FIELDS = ("tuition_basis", "tuition_amount_usd", "tuition_year")


def _retrieved_on(call):
    return date.fromisoformat(call["retrieved_at"][:10])


class _Builder:
    def __init__(self, call, meta, audience="applicants", stem_ref=None):
        self.call, self.meta, self.audience, self.stem_ref = call, meta, audience, stem_ref
        self.rows = []

    def add(self, field, status, value=None, entry=None, term=None, review=(), group_id="", group_key="", extras=None,
            derived=None):
        entry = entry or {}
        n = len(self.rows)
        raw = f"{self.meta['call_id']}|{self.call['program_id']}|{self.call['page_id']}|{EXTRACT_RULES_VERSION}|{n}"
        self.rows.append({
            "observation_id": "obs-" + hashlib.sha256(raw.encode()).hexdigest()[:16],
            "call_id": self.meta["call_id"], "snapshot_id": self.call["snapshot_id"],
            "program_id": self.call["program_id"], "page_id": self.call["page_id"],
            "owner_level": self.call["owner_level"], "field": field, "value": value, "value_status": status,
            "reference_target": entry.get("reference_target"),
            "valid_for_term": term.valid_for_term if term else "", "term_as_written": entry.get("term_as_written"),
            "term_basis": term.term_basis if term else "unknown", "stale": term.stale if term else False,
            "conflict_type": [], "group_id": group_id, "group_key": group_key,
            "evidence_text": entry.get("evidence_text"), "evidence_url": self.call["final_url"],
            "retrieved_at": self.call["retrieved_at"], "confidence": entry.get("confidence"),
            "other_program_mentioned": entry.get("other_program_mentioned"),
            "excluded_by_scope_note": bool(entry.get("excluded_by_scope_note")),
            "audience": self.audience, "snapshot_classification": self.call["classification"],
            "review_from_rules": list(review), "extras": extras or {}, "derived": derived or {},
            "model_name": self.meta["model_name"], "prompt_version": self.meta["prompt_version"],
            "schema_version": self.meta["schema_version"], "extract_rules_version": EXTRACT_RULES_VERSION,
            "extracted_at": self.meta["extracted_at"],
        })


def _failed(builder, key, reasons):
    review = [f"evidence_failed:{r}" for r in reasons]
    for field in OBSERVATION_FIELDS.get(key, (key,)):
        builder.add(field, "extraction_failed", review=review)


def _deadline(builder, entry):
    if entry["value_status"] != "found":
        builder.add("deadline", entry["value_status"], entry=entry)
        return
    call = builder.call
    term = deadline_term(entry["term_as_written"], entry["deadline_month"], entry["deadline_day"],
                         entry["deadline_year"], call["intake_terms"], _retrieved_on(call))
    kind, scope, round_name = entry["deadline_type"] or "application", entry["applicant_scope"] or "all", \
        entry["round_name"] or ""
    value = {"deadline_date": term.deadline_date.isoformat() if term.deadline_date else None, "round_name": round_name,
             "deadline_type": kind, "deadline_tz": entry["deadline_tz"], "applicant_scope": scope,
             "is_rolling": bool(entry["is_rolling"])}
    builder.add("deadline", "found", value, entry, term, term.review, group_key=f"{kind}|{scope}|{round_name}")


def _tuition(builder, entry, index):
    if entry["value_status"] != "found":
        for field in TUITION_FIELDS:
            builder.add(field, entry["value_status"], entry=entry)
        return
    term = tuition_term(entry["term_as_written"], builder.call["intake_terms"])
    group_id = f"{builder.meta['call_id']}-t{index}"
    basis = entry["tuition_basis"]
    year = entry["tuition_year"] or academic_year_as_written(entry["term_as_written"])
    key = f"{basis or ''}|{year or ''}"
    extras = {"includes_fees": bool(entry["includes_fees"])}
    if basis:
        builder.add("tuition_basis", "found", basis, entry, term, term.review, group_id, key)
    else:
        builder.add("tuition_basis", "not_mentioned", group_id=group_id, group_key=key)
    review = [*term.review, *(() if basis else ("tuition_basis_missing",))]     # 08 §3.1
    builder.add("tuition_amount_usd", "found", entry["tuition_amount_usd"], entry, term, review, group_id, key, extras)
    if year:
        builder.add("tuition_year", "found", year, entry, term, term.review, group_id, key)
    else:
        builder.add("tuition_year", "not_mentioned", group_id=group_id, group_key=key)


def _toefl(builder, entries):
    scales, conflicts = set(), []
    no_value = []
    for entry in entries:
        if entry["value_status"] != "found":
            no_value.append(entry)
            continue
        scale, problem = toefl_scale(entry["value"], entry["evidence_text"])
        if problem == "unrecognized" or (problem and _by_value(entry["value"]) is None):
            builder.add(TOEFL_FIELDS["legacy"], "extraction_failed", review=["toefl_scale_unrecognized"])
            continue
        scale = scale or _by_value(entry["value"])
        term = undated_term(entry["term_as_written"], builder.call["intake_terms"])
        scales.add(scale)
        extras = {"conditional_admission_range": entry["conditional_admission_range"]}
        builder.add(TOEFL_FIELDS[scale], "found", _toefl_number(entry["value"], scale), entry, term, term.review,
                    extras=extras)
        if problem:
            conflicts.append(builder.rows[-1])          # 08 §9: the written scale contradicts the number
    for field in TOEFL_FIELDS.values():
        if not any(r["field"] == field for r in builder.rows):
            if no_value:
                builder.add(field, no_value[0]["value_status"], entry=no_value[0])
            else:
                builder.add(field, "not_mentioned")
    if scales:
        builder.add("toefl_scale_on_page", "found", "both" if len(scales) == 2 else next(iter(scales)))
    elif no_value:
        builder.add("toefl_scale_on_page", no_value[0]["value_status"], entry=no_value[0])
    else:
        builder.add("toefl_scale_on_page", "not_mentioned")
    return conflicts


def _by_value(value):
    _, problem = toefl_scale(value, "")
    return None if problem else toefl_scale(value, "")[0]


def _toefl_number(value, scale):
    return int(value) if scale == "legacy" else float(value)


def _simple(builder, key, entry):
    if entry["value_status"] != "found":
        builder.add(key, entry["value_status"], entry=entry)
        return
    term = undated_term(entry["term_as_written"], builder.call["intake_terms"])
    extras, derived = {}, {}
    if "conditional_admission_range" in entry:
        extras["conditional_admission_range"] = entry["conditional_admission_range"]
    value = entry["value"]
    if key == "cip_code":
        value = value.strip()
        extras["cip_context"] = entry["cip_context"]
        derived["cip_source"] = cip_source(entry["cip_context"], builder.call["page_type"])
        if builder.stem_ref is not None:
            derived["stem_status"] = stem_status(value, derived["cip_source"], builder.stem_ref)
    builder.add(key, "found", value, entry, term, term.review, extras=extras, derived=derived)


def build_rows(call, output, page_text, meta, stem_ref=None):
    """Observation rows for one successful call; in-page conflicts are written here (08 §8)."""
    builder = _Builder(call, meta, output["audience"], stem_ref)
    scale_conflicts = []
    for key in GROUPS:
        entries = output[key]
        good = []
        for i, entry in enumerate(entries):
            reasons = check_entry(key, entry, page_text)
            if reasons:
                _failed(builder, key, reasons)
            else:
                good.append((i, entry))
        if not entries:
            for field in OBSERVATION_FIELDS.get(key, (key,)):
                builder.add(field, "not_mentioned")
        elif key == "toefl_total":
            scale_conflicts = _toefl(builder, [e for _, e in good]) if good else []
        else:
            for i, entry in good:
                if key == "deadlines":
                    _deadline(builder, entry)
                elif key == "tuition":
                    _tuition(builder, entry, i)
                else:
                    _simple(builder, key, entry)
    conflicts = in_page_conflicts(builder.rows)
    for row in builder.rows:
        row["conflict_type"] = conflicts[id(row)]
    for row in scale_conflicts:
        if "in_page_contradiction" not in row["conflict_type"]:
            row["conflict_type"].append("in_page_contradiction")
    return builder.rows


def failure_rows(call, meta, status, review=()):
    """One row per field when a whole call fails (extraction_failed) or the page is unavailable (05 §4)."""
    builder = _Builder(call, meta)
    for field in ALL_FIELDS:
        builder.add(field, status, review=list(review))
    return builder.rows
