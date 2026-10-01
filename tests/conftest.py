import json

import pytest

from helpers import FIXTURES, REGISTRY_FIXTURES, REPO, copy_registry, read_str_csv


@pytest.fixture
def fixtures():
    return FIXTURES


@pytest.fixture
def cip2020():
    """CIP 2020 in derived-table format (data/ref/cip2020.csv), built by hand."""
    return read_str_csv(FIXTURES / "cip2020_ref_sample.csv")


@pytest.fixture
def stem_ref(cip2020):
    from gradprog.ref.stem import StemReference

    return StemReference(
        read_str_csv(FIXTURES / "stem_list_sample.csv"),
        read_str_csv(FIXTURES / "stem_core_series_sample.csv"),
        cip2020,
    )


@pytest.fixture
def stem_words():
    return json.loads((FIXTURES / "stem_pdf_words.json").read_text(encoding="utf-8"))


@pytest.fixture
def targets(cip2020):
    from gradprog.ref.targets import expand_targets, load_target_config

    return expand_targets(load_target_config(REPO / "config" / "target_cip.csv"), cip2020)


@pytest.fixture
def registry_candidates():
    return read_str_csv(REGISTRY_FIXTURES / "candidates_sample.csv")


@pytest.fixture
def registry_dir(tmp_path):
    return copy_registry(tmp_path / "registry")


@pytest.fixture
def registry(registry_dir):
    from gradprog.registry.tables import load_registry

    return load_registry(registry_dir)
