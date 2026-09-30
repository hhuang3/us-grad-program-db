"""CIP code normalization and CIP 2020 parsing (docs/spec/03_stem_logic.md §1, 01 §2)."""


class CipFormatError(ValueError):
    """Input cannot be normalized to a standard CIP format."""


class UnknownCipError(ValueError):
    """Well-formed CIP code that is not a valid CIP 2020 code."""


def normalize_cip6(value):
    raise NotImplementedError


def normalize_cip4(value):
    raise NotImplementedError


def parse_cip2020_csv(path):
    raise NotImplementedError


def is_valid_cip2020(code6, cip2020):
    raise NotImplementedError
