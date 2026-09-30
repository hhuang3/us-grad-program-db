"""Target CIP configuration (docs/spec/04_candidate_selection.md §1)."""


class TargetCipError(ValueError):
    """Target CIP configuration is inconsistent with CIP 2020."""


def load_target_config(path):
    raise NotImplementedError


def expand_targets(config, cip2020, must_exist=None):
    raise NotImplementedError
