"""URL normalization and domain derivation (06 §3.5)."""


class UrlError(ValueError):
    """URL cannot be accepted into the registry."""


def normalize_url(url):
    raise NotImplementedError


def domain_of(url):
    raise NotImplementedError
