"""v1 extraction fields and the LLM output schema built from them (08 §3, §4, §4.1)."""

LLM_STATUSES = ("found", "referenced_elsewhere", "mentioned_without_value")   # [] means not_mentioned (08 §4.1)
AUDIENCES = ("applicants", "current_students", "other_program")
POLICIES = ("required", "optional", "not_required", "not_accepted", "conditional_waiver")
TUITION_BASES = ("per_credit", "per_term", "per_year", "program_total")
DEADLINE_TYPES = ("application", "international_docs", "deposit", "decision_release", "other")
APPLICANT_SCOPES = ("all", "international", "domestic", "funding_consideration")
CIP_CONTEXTS = ("stem_list", "program_intro", "i20_statement", "other")
STEM_CLAIMS = ("yes", "no")


def _opt(kind):
    return {"type": [kind, "null"]}


def _opt_enum(values):
    return {"anyOf": [{"type": "string", "enum": list(values)}, {"type": "null"}]}


NUMBER, INTEGER, STRING, BOOLEAN = _opt("number"), _opt("integer"), _opt("string"), _opt("boolean")

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
                  "deadline_type": _opt_enum(DEADLINE_TYPES), "deadline_tz": STRING,
                  "applicant_scope": _opt_enum(APPLICANT_SCOPES), "is_rolling": BOOLEAN},
    "toefl_total": {"value": NUMBER, "conditional_admission_range": STRING},
    "ielts_min_overall": {"value": NUMBER, "conditional_admission_range": STRING},
    "gre_policy": {"value": _opt_enum(POLICIES)},
    "gmat_policy": {"value": _opt_enum(POLICIES)},
    "tuition": {"tuition_basis": _opt_enum(TUITION_BASES), "tuition_amount_usd": NUMBER, "tuition_year": STRING,
                "includes_fees": BOOLEAN},
    "length_months_min": {"value": INTEGER},
    "length_months_max": {"value": INTEGER},
    "credits_required": {"value": INTEGER},
    "cip_code": {"value": STRING, "cip_context": _opt_enum(CIP_CONTEXTS)},
    "stem_claim_on_page": {"value": _opt_enum(STEM_CLAIMS)},
    "app_fee_usd": {"value": NUMBER},
}

# observation field names produced from each LLM output key (08 §4.1)
OBSERVATION_FIELDS = {
    "deadlines": ("deadline",),
    "toefl_total": ("toefl_min_legacy", "toefl_min_new_scale", "toefl_scale_on_page"),
    "tuition": ("tuition_basis", "tuition_amount_usd", "tuition_year"),
}
ALL_FIELDS = tuple(f for key in GROUPS for f in OBSERVATION_FIELDS.get(key, (key,)))


def build_schema():
    """The JSON schema sent to the API (numeric ranges are not supported there; 08 §6 checks them in code)."""
    properties = {
        "terms_mentioned": {"type": "array", "items": {"type": "string"}},
        "audience": {"type": "string", "enum": list(AUDIENCES)},
    }
    for key, extra in GROUPS.items():
        entry = {**COMMON, **extra}
        properties[key] = {"type": "array", "items": {
            "type": "object", "properties": entry, "required": list(entry), "additionalProperties": False}}
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def _type_ok(value, kind):
    if kind == "null":
        return value is None
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, {"string": str, "array": list, "object": dict}[kind])


def schema_errors(value, schema, path="$"):
    """Errors of `value` against the subset of JSON schema used by build_schema (08 §1)."""
    if "anyOf" in schema:
        if any(not schema_errors(value, s, path) for s in schema["anyOf"]):
            return []
        return [f"{path}: matches no allowed form"]
    kinds = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
    if not any(_type_ok(value, k) for k in kinds):
        return [f"{path}: expected {'/'.join(kinds)}"]
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
