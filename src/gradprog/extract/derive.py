"""Values worked out by code, never by the LLM (08 §3.1, §3.2)."""

from gradprog.ref.stem import derive_stem_status


def cip_source(cip_context, page_type):
    """08 §3.2. `ipeds_inferred` is never produced here: this only sees CIP codes written on a page."""
    if cip_context == "stem_list" or page_type == "isso_stem_list":
        return "school_stem_page"
    if cip_context == "i20_statement":
        return "i20_statement"
    return "program_page"


def stem_status(cip_code, source, ref):
    return derive_stem_status(cip_code, source, ref)


def tuition_total(basis, amount, credits=None, terms=None, years=None):
    """(estimate, method). Terms and years come from a reviewer, not from a guess (08 §3.1); missing input: (None, "")."""
    if amount is None:
        return None, ""
    if basis == "program_total":
        return amount, "program_total"
    if basis == "per_credit" and credits:
        return amount * credits, f"per_credit x {credits} credits"
    if basis == "per_term" and terms:
        return amount * terms, f"per_term x {terms} terms"
    if basis == "per_year" and years:
        return amount * years, f"per_year x {years} years"
    return None, ""
