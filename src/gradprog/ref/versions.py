"""Derive the data version of committed reference tables (docs/spec/01_reference_data.md §8)."""


class VersionError(ValueError):
    """The data version cannot be derived unambiguously."""


def ipeds_version(data_year):
    raise NotImplementedError


def scorecard_release(manifest_path, derived_path):
    raise NotImplementedError
