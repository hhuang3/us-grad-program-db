"""URL normalization and domain derivation (06 §3.5)."""

from urllib.parse import urlsplit, urlunsplit

TRACKING_EXACT = frozenset({"gclid", "fbclid", "msclkid", "mc_cid", "mc_eid", "_ga", "_gl"})
TRACKING_PREFIXES = ("utm_", "hsa_")


class UrlError(ValueError):
    """URL cannot be accepted into the registry."""


def _is_tracking(param):
    name = param.split("=", 1)[0].lower()
    return name in TRACKING_EXACT or name.startswith(TRACKING_PREFIXES)


def normalize_url(url):
    if not isinstance(url, str):
        raise UrlError(f"URL must be a string, got {url!r}")
    parts = urlsplit(url.strip())
    if parts.scheme.lower() != "https":
        raise UrlError(f"URL must use https (http is not upgraded automatically): {url!r}")
    if parts.username is not None or parts.password is not None:
        raise UrlError(f"URL must not contain credentials: {url!r}")
    host = (parts.hostname or "").rstrip(".")
    if not host:
        raise UrlError(f"URL has no host: {url!r}")
    try:
        port = parts.port
    except ValueError as e:
        raise UrlError(f"URL has an invalid port: {url!r}") from e
    netloc = host if port in (None, 443) else f"{host}:{port}"
    # Split the raw query by hand so values are never decoded or re-encoded.
    query = "&".join(p for p in parts.query.split("&") if p and not _is_tracking(p))
    return urlunsplit(("https", netloc, parts.path or "/", query, ""))


def domain_of(url):
    return urlsplit(normalize_url(url)).hostname
