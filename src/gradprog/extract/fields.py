"""v1 extraction fields and the LLM output schema built from them (08 §3, §4, §4.1)."""

LLM_STATUSES = ("found", "referenced_elsewhere", "mentioned_without_value")   # [] means not_mentioned (08 §4.1)
AUDIENCES = ("applicants", "current_students", "other_program")
POLICIES = ("required", "optional", "not_required", "not_accepted", "conditional_waiver")
TUITION_BASES = ("per_credit", "per_term", "per_year", "program_total")
DEADLINE_TYPES = ("application", "international_docs", "deposit", "decision_release", "other")
APPLICANT_SCOPES = ("all", "international", "domestic", "funding_consideration")
CIP_CONTEXTS = ("stem_list", "program_intro", "i20_statement", "other")
STEM_CLAIMS = ("yes", "no")


NONE = "none"   # the API allows few union types (08 §4.1), so "no value" is "", 0, false or this enum member


def _enum(values):
    return {"type": "string", "enum": [*values, NONE]}


NUMBER, INTEGER, STRING, BOOLEAN = {"type": "number"}, {"type": "integer"}, {"type": "string"}, {"type": "boolean"}

COMMON = {
    "value_status": {"type": "string", "enum": list(LLM_STATUSES)},
    "reference_target": STRING,
    "evidence_text": STRING,
    "term_as_written": STRING,
    "confidence": {"type": "number"},
    "other_program_mentioned": STRING,
    "excluded_by_scope_note": {"type": "boolean"},
}

# LLM output key -> properties of one entry, on top of COMMON
GROUPS = {
    "deadlines": {"deadline_month": INTEGER, "deadline_day": INTEGER, "deadline_year": INTEGER, "round_name": STRING,
                  "deadline_type": _enum(DEADLINE_TYPES), "deadline_tz": STRING,
                  "applicant_scope": _enum(APPLICANT_SCOPES), "is_rolling": BOOLEAN},
    "toefl_total": {"value": NUMBER, "conditional_admission_range": STRING},
    "ielts_min_overall": {"value": NUMBER, "conditional_admission_range": STRING},
    "gre_policy": {"value": _enum(POLICIES)},
    "gmat_policy": {"value": _enum(POLICIES)},
    "tuition": {"tuition_basis": _enum(TUITION_BASES), "tuition_amount_usd": NUMBER, "tuition_year": STRING,
                "includes_fees": BOOLEAN},
    "length_months_min": {"value": INTEGER},
    "length_months_max": {"value": INTEGER},
    "credits_required": {"value": INTEGER},
    "cip_code": {"value": STRING, "cip_context": _enum(CIP_CONTEXTS)},
    "stem_claim_on_page": {"value": _enum(STEM_CLAIMS)},
    "app_fee_usd": {"value": NUMBER},
}

# observation field names produced from each LLM output key (08 §4.1)
OBSERVATION_FIELDS = {
    "deadlines": ("deadline",),
    "toefl_total": ("toefl_min_legacy", "toefl_min_new_scale", "toefl_scale_on_page"),
    "tuition": ("tuition_basis", "tuition_amount_usd", "tuition_year"),
}
ALL_FIELDS = tuple(f for key in GROUPS for f in OBSERVATION_FIELDS.get(key, (key,)))


NUMBER_KEYS = ("toefl_total", "ielts_min_overall", "length_months_min", "length_months_max", "credits_required",
               "app_fee_usd")
WHOLE_KEYS = ("length_months_min", "length_months_max", "credits_required")
OWN_ARRAY_KEYS = ("deadlines", "tuition")
SIMPLE_KEYS = tuple(k for k in GROUPS if k not in OWN_ARRAY_KEYS)


def _array_of(properties):
    return {"type": "array", "items": {
        "type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}}


def build_schema():
    """The JSON schema sent to the API (08 §4.1).

    The API limits the compiled size, so deadlines and tuition get arrays of their own and all other fields share one.
    It has no numeric ranges either: 08 §6 checks those in code.
    """
    properties = {
        "terms_mentioned": {"type": "array", "items": {"type": "string"}},
        "audience": {"type": "string", "enum": list(AUDIENCES)},
        "deadlines": _array_of({**COMMON, **GROUPS["deadlines"]}),
        "tuition": _array_of({**COMMON, **GROUPS["tuition"]}),
        "fields": _array_of({"field": {"type": "string", "enum": list(SIMPLE_KEYS)}, **COMMON, "number_value": NUMBER,
                             "text_value": STRING, "conditional_admission_range": STRING,
                             "cip_context": _enum(CIP_CONTEXTS)}),
    }
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def _type_ok(value, kind):
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, {"string": str, "array": list, "object": dict}[kind])


def schema_errors(value, schema, path="$"):
    """Errors of `value` against the subset of JSON schema used by build_schema (08 §1)."""
    if not _type_ok(value, schema["type"]):
        return [f"{path}: expected {schema['type']}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path}: value not in enum"]
    errors = []
    if isinstance(value, dict):
        for name in schema["required"]:
            if name not in value:
                errors.append(f"{path}.{name}: missing")
        for name, item in value.items():
            if name not in schema["properties"]:
                errors.append(f"{path}.{name}: unexpected")
            else:
                errors.extend(schema_errors(item, schema["properties"][name], f"{path}.{name}"))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            errors.extend(schema_errors(item, schema["items"], f"{path}[{i}]"))
    return errors


def _blank_to_none(entry, enums):
    return {k: None if v == "" or (v == NONE and k in enums) else v for k, v in entry.items()}


def _simple_entry(wire):
    key = wire["field"]
    entry = {k: wire[k] for k in COMMON}
    value = wire["number_value"] if key in NUMBER_KEYS else wire["text_value"]
    if key in WHOLE_KEYS and isinstance(value, float) and value.is_integer():
        value = int(value)
    entry["value"] = value
    if "conditional_admission_range" in GROUPS[key]:
        entry["conditional_admission_range"] = wire["conditional_admission_range"]
    if "cip_context" in GROUPS[key]:
        entry["cip_context"] = wire["cip_context"]
    return key, entry


def from_wire(output):
    """The API's output as one array per field, with "no value" as None (08 §4.1).

    Nothing is kept beside a status other than found (05 §4). A key with no entries means not_mentioned.
    """
    out = {"terms_mentioned": output["terms_mentioned"], "audience": output["audience"], **{k: [] for k in GROUPS}}
    pairs = [(k, e) for k in OWN_ARRAY_KEYS for e in output[k]] + [_simple_entry(w) for w in output["fields"]]
    for key, raw in pairs:
        enums = {k for k, s in {**COMMON, **GROUPS[key]}.items() if "enum" in s}
        entry = _blank_to_none(raw, enums)
        if entry["value_status"] != "found":
            entry.update(dict.fromkeys(GROUPS[key]))
        if key == "deadlines":
            for part in ("deadline_month", "deadline_day", "deadline_year"):
                entry[part] = entry[part] or None
        out[key].append(entry)
    return out
