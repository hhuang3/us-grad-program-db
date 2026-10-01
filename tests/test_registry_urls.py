"""docs/spec/06_source_registry.md §3.5: URL normalization and domain derivation."""

import pytest

from gradprog.registry.urls import UrlError, domain_of, normalize_url


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("https://grad.wisc.edu/apply/", "https://grad.wisc.edu/apply/"),
        ("  https://grad.wisc.edu/apply  ", "https://grad.wisc.edu/apply"),
        ("https://Grad.WISC.edu/Apply/", "https://grad.wisc.edu/Apply/"),        # host lowercased, path case kept
        ("https://grad.wisc.edu./apply", "https://grad.wisc.edu/apply"),          # trailing dot in host
        ("https://grad.wisc.edu:443/apply", "https://grad.wisc.edu/apply"),       # default port
        ("https://grad.wisc.edu:8443/apply", "https://grad.wisc.edu:8443/apply"), # non-default port kept
        ("https://grad.wisc.edu/apply#deadlines", "https://grad.wisc.edu/apply"),
        ("https://grad.wisc.edu", "https://grad.wisc.edu/"),                      # empty path -> /
        ("https://grad.wisc.edu/apply?utm_source=x&utm_medium=y", "https://grad.wisc.edu/apply"),
        ("https://grad.wisc.edu/apply?UTM_Campaign=x&term=fall", "https://grad.wisc.edu/apply?term=fall"),
        ("https://grad.wisc.edu/a?b=2&gclid=1&a=1&fbclid=2", "https://grad.wisc.edu/a?b=2&a=1"),  # order kept
        ("https://grad.wisc.edu/a?msclkid=1&mc_cid=2&mc_eid=3&_ga=4&_gl=5&hsa_acc=6", "https://grad.wisc.edu/a"),
        ("https://grad.wisc.edu/a%20b?q=a%2Fb", "https://grad.wisc.edu/a%20b?q=a%2Fb"),  # no re-encoding
        ("https://grad.wisc.edu/apply/?term=fall#x", "https://grad.wisc.edu/apply/?term=fall"),
    ],
)
def test_normalize_url(raw, expected):
    assert normalize_url(raw) == expected


def test_normalize_is_idempotent():
    url = "https://Grad.wisc.edu:443/Apply/?utm_source=x&term=fall#top"
    once = normalize_url(url)
    assert normalize_url(once) == once


@pytest.mark.parametrize(
    "raw",
    [
        "http://grad.wisc.edu/apply",            # not upgraded automatically
        "ftp://grad.wisc.edu/file",
        "grad.wisc.edu/apply",
        "https://user:pw@grad.wisc.edu/apply",   # credentials
        "https:///apply",
        "",
    ],
)
def test_normalize_url_rejects(raw):
    with pytest.raises(UrlError):
        normalize_url(raw)


@pytest.mark.parametrize(
    "raw, domain",
    [
        ("https://Grad.WISC.edu/apply", "grad.wisc.edu"),
        ("https://www.stat.wisc.edu./", "www.stat.wisc.edu"),
        ("https://grad.wisc.edu:443/x", "grad.wisc.edu"),
    ],
)
def test_domain_of(raw, domain):
    assert domain_of(raw) == domain


def test_url_error_is_value_error_and_names_input():
    with pytest.raises(ValueError) as exc:
        normalize_url("http://grad.wisc.edu/apply")
    assert isinstance(exc.value, UrlError)
    assert "http://grad.wisc.edu/apply" in str(exc.value)
