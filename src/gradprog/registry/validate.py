"""Registry validation (06 §5)."""


class ValidationResult:
    def __init__(self, errors, warnings, report):
        raise NotImplementedError


def load_head_tables(repo_root, registry_rel="data/registry"):
    raise NotImplementedError


def validate(registry, candidates, previous=None, ready=False, batch=None):
    raise NotImplementedError
