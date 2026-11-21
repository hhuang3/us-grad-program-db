"""Display names derived from the registry (06 §3.1): the degree abbreviation of degree_type = other."""

import re

IN_PARENTHESES = re.compile(r"\(([A-Z][A-Za-z]{1,5})\)")
LEADING = re.compile(r"^([A-Z]{2,6})\s*[:\-–]")


def degree_abbreviation(program_name):
    """"MQE" from "Master of Quantitative Economics (MQE)", "MQM" from "MQM: Business Analytics"; else None."""
    name = program_name or ""
    m = LEADING.match(name.strip())
    if m:
        return m.group(1)
    found = IN_PARENTHESES.findall(name)
    return found[-1] if found else None


def degree_name(program):
    """degree_label when set; the abbreviation in the name for degree_type = other; else degree_type in capitals."""
    if program.get("degree_label"):
        return program["degree_label"]
    if program["degree_type"] == "other":
        return degree_abbreviation(program["program_name"])
    return program["degree_type"].upper()
