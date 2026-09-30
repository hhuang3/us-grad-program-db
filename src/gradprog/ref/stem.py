"""DHS STEM list parsing and STEM logic (docs/spec/03_stem_logic.md)."""


class StemParseError(ValueError):
    """The STEM list PDF does not match the documented structure."""


def extract_pdf_words(path):
    raise NotImplementedError


def parse_core_series_from_intro(text):
    raise NotImplementedError


def parse_stem_words(pages, cip2020):
    raise NotImplementedError


class StemReference:
    def __init__(self, stem_list, core_series, cip2020):
        raise NotImplementedError

    @classmethod
    def load(cls, ref_dir):
        raise NotImplementedError


def cip_on_stem_list(cip, ref):
    raise NotImplementedError


def cip_on_stem_list_exact(cip, ref):
    raise NotImplementedError


def expansion_only_codes(ref):
    raise NotImplementedError


def derive_stem_status(cip_code, cip_source, ref):
    raise NotImplementedError
