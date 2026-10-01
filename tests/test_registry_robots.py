"""docs/spec/06_source_registry.md §4: robots.txt checks (offline, httpx.MockTransport) and crawl permission."""

import httpx
import pytest

from gradprog.registry.robots import check_robots, crawl_allowed_for, robots_verdicts
from gradprog.util.download import DownloadError, user_agent

EMAIL = "someone@example.com"
NOW = "2026-10-03T09:00:00Z"
URLS = ["https://grad.alpha.edu/admissions/international", "https://grad.alpha.edu/private/tuition.pdf"]


# --- robots_verdicts: pure decision function ----------------------------------

def test_verdict_allow_all():
    status, v = robots_verdicts(200, "User-agent: *\nDisallow:\n", URLS)
    assert status == "fetched"
    assert v == {u: "yes" for u in URLS}


def test_verdict_disallow_all():
    status, v = robots_verdicts(200, "User-agent: *\nDisallow: /\n", URLS)
    assert status == "fetched"
    assert v == {u: "no" for u in URLS}


def test_verdict_partial_path():
    status, v = robots_verdicts(200, "User-agent: *\nDisallow: /private/\n", URLS)
    assert v == {URLS[0]: "yes", URLS[1]: "no"}


def test_verdict_uses_our_agent_token():
    text = "User-agent: gradprog-refdata\nDisallow: /admissions/\n\nUser-agent: *\nDisallow:\n"
    _, v = robots_verdicts(200, text, URLS)
    assert v == {URLS[0]: "no", URLS[1]: "yes"}


@pytest.mark.parametrize("code", [404, 410])
def test_verdict_not_found_allows(code):
    status, v = robots_verdicts(code, "", URLS)
    assert status == "not_found"
    assert set(v.values()) == {"yes"}


@pytest.mark.parametrize("code", [401, 403, 400, 429, 500, 503])
def test_verdict_other_errors_disallow(code):
    status, v = robots_verdicts(code, "User-agent: *\nDisallow:\n", URLS)
    assert status == "error"
    assert set(v.values()) == {"no"}


def test_verdict_network_error_disallows():
    status, v = robots_verdicts(None, "", URLS)
    assert status == "error"
    assert set(v.values()) == {"no"}


# --- crawl_allowed_for (§4.3) -------------------------------------------------

def test_crawl_allowed_matches_fixture(registry):
    got = list(crawl_allowed_for(registry.pages, registry.domains))
    assert got == list(registry.pages["crawl_allowed"])
    assert got == ["true", "true", "false", "false", "false"]


@pytest.mark.parametrize(
    "robots_allowed, tos, expected",
    [
        ("yes", "no_restriction", "true"),
        ("yes", "unclear", "false"),
        ("yes", "prohibits_automated_access", "false"),
        ("yes", "not_checked", "false"),
        ("no", "no_restriction", "false"),
        ("not_checked", "no_restriction", "false"),
    ],
)
def test_crawl_allowed_truth_table(registry, robots_allowed, tos, expected):
    registry.pages.loc[registry.pages["page_id"] == "pg-0001", "robots_allowed"] = robots_allowed
    registry.domains.loc[registry.domains["domain"] == "datascience.alpha.edu", "tos_status"] = tos
    got = dict(zip(registry.pages["page_id"], crawl_allowed_for(registry.pages, registry.domains)))
    assert got["pg-0001"] == expected


# --- check_robots with MockTransport ------------------------------------------

class FakeTime:
    def __init__(self):
        self.t = 0.0
        self.slept = []

    def clock(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


ROBOTS = {
    "datascience.alpha.edu": (200, "User-agent: *\nDisallow:\n"),
    "grad.alpha.edu": (404, "not here"),
    "business.alpha.edu": (200, "User-agent: *\nDisallow: /msba/admissions\n"),
}


def run(registry, responses=ROBOTS, seen=None):
    fake = FakeTime()

    def handler(request):
        if seen is not None:
            seen.append((request.url.host, request.url.path, request.headers["user-agent"]))
        code, text = responses[request.url.host]
        return httpx.Response(code, text=text)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    check_robots(registry, contact_email=EMAIL, client=client, clock=fake.clock, sleep=fake.sleep, now=lambda: NOW)
    return fake


def test_check_robots_writes_page_and_domain_results(registry):
    run(registry)
    pages = registry.pages.set_index("page_id")
    assert pages.loc["pg-0001", "robots_allowed"] == "yes"
    assert pages.loc["pg-0002", "robots_allowed"] == "yes"     # 404 -> allowed
    assert pages.loc["pg-0005", "robots_allowed"] == "yes"     # was not_checked
    assert pages.loc["pg-0003", "robots_allowed"] == "yes"
    assert pages.loc["pg-0004", "robots_allowed"] == "no"
    d = registry.domains.set_index("domain")
    assert d.loc["grad.alpha.edu", "robots_status"] == "not_found"
    assert d.loc["business.alpha.edu", "robots_allows_registered_paths"] == "partial"
    assert d.loc["datascience.alpha.edu", "robots_allows_registered_paths"] == "yes"
    assert set(d["robots_checked_at"]) == {NOW}


def test_check_robots_recomputes_crawl_allowed(registry):
    run(registry)
    crawl = dict(zip(registry.pages["page_id"], registry.pages["crawl_allowed"]))
    assert crawl == {"pg-0001": "true", "pg-0002": "true", "pg-0003": "false",   # business tos unclear
                     "pg-0004": "false", "pg-0005": "true"}


def test_check_robots_server_error_disallows_domain(registry):
    responses = dict(ROBOTS, **{"grad.alpha.edu": (503, "")})
    run(registry, responses)
    pages = registry.pages.set_index("page_id")
    assert pages.loc["pg-0002", "robots_allowed"] == "no"
    d = registry.domains.set_index("domain")
    assert d.loc["grad.alpha.edu", "robots_status"] == "error"
    assert d.loc["grad.alpha.edu", "robots_allows_registered_paths"] == "no"


def test_check_robots_domain_without_pages_is_no_pages(registry):
    registry.domains.loc[len(registry.domains)] = ["empty.alpha.edu", "https://empty.alpha.edu/robots.txt",
                                                   "", "", "", "", "not_checked", ""]
    run(registry, dict(ROBOTS, **{"empty.alpha.edu": (200, "User-agent: *\nDisallow: /\n")}))
    assert registry.domains.set_index("domain").loc["empty.alpha.edu", "robots_allows_registered_paths"] == "no_pages"


def test_check_robots_requests_robots_txt_with_our_user_agent(registry):
    seen = []
    run(registry, seen=seen)
    assert {(h, p) for h, p, _ in seen} == {(d, "/robots.txt") for d in ROBOTS}
    assert {ua for _, _, ua in seen} == {user_agent(EMAIL)}


def test_check_robots_spaces_requests(registry):
    fake = run(registry)
    assert len(fake.slept) == len(ROBOTS) - 1
    assert all(s >= 3.0 for s in fake.slept)


def test_check_robots_requires_contact_email(registry, monkeypatch):
    monkeypatch.delenv("GRADPROG_CONTACT_EMAIL", raising=False)
    with pytest.raises(DownloadError, match="GRADPROG_CONTACT_EMAIL"):
        check_robots(registry, client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
