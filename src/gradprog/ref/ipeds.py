"""IPEDS Completions filtering and candidate list (docs/spec/04_candidate_selection.md §3–4)."""


class IpedsError(ValueError):
    """IPEDS input violates a documented rule."""


def select_revised_member(names):
    raise NotImplementedError


def read_ipeds_csv(path):
    raise NotImplementedError


def build_ipeds_masters_target(completions, hd, targets, data_year):
    raise NotImplementedError


def build_candidates(ipeds_table, hd, cip2020, stem_ref):
    raise NotImplementedError


def build_candidates_by_institution(candidates):
    raise NotImplementedError
