"""docs/spec/06_source_registry.md §3.1: degree names for display."""

import pytest

from gradprog.registry.names import degree_abbreviation, degree_name


@pytest.mark.parametrize("name,abbr", [
    ("Master of Quantitative Economics (MQE)", "MQE"),
    ("MQM: Business Analytics (Master of Quantitative Management)", "MQM"),
    ("Master of Science in Business Analytics (MSA)", "MSA"),
    ("MS Applied Economics and Econometrics (MS AEE)", None),
    ("Master of Data Things", None),
])
def test_abbreviation_from_the_program_name(name, abbr):
    assert degree_abbreviation(name) == abbr


def test_degree_name_prefers_the_label_then_the_name():
    base = {"degree_type": "other", "degree_label": "", "program_name": "Master of Quantitative Economics (MQE)"}
    assert degree_name(base) == "MQE"
    assert degree_name({**base, "degree_label": "MQEcon"}) == "MQEcon"
    assert degree_name({**base, "degree_type": "ms"}) == "MS"
