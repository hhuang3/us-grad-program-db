"""docs/spec/06_source_registry.md §4.4: check-urls (offline, httpx.MockTransport)."""

import copy

import httpx
import pytest

from gradprog.registry.url_check import check_urls, write_url_check
from gradprog.util.download import DownloadError, user_agent

EMAIL = "someone@example.com"
NOW = "2026-10-03T09:00:00Z"
COLUMNS = ["page_id", "url", "result", "http_status", "final_url", "checked_at"]

ROBOTS = {
    "datascience.alpha.edu": (200, "User-agent: *\nDisallow:\n"),
    "grad.alpha.edu": (404, ""),
    "business.alpha.edu": (200, "User-agent: *\nDisallow: /msba/admissions\n"),
}


def default_pages(request):
    url = str(request.url)
    if url == "https://datascience.alpha.edu/ms":
        return httpx.Response(301, headers={"Location": "https://datascience.alpha.edu/programs/ms"})
    if url == "https://datascience.alpha.edu/programs/ms":
        return httpx.Response(200, text="<html>new page</html>")
    if url == "https://grad.alpha.edu/admissions/international":
        return httpx.Response(404, text="not found")
    if url == "https://business.alpha.edu/msba":
        return httpx.Response(302, headers={"Location": "https://business.alpha.edu/msba?utm_source=redirect"})
    if url == "https://business.alpha.edu/msba?utm_source=redirect":
        return httpx.Response(200, text="<html>same page</html>")
    if url == "https://grad.alpha.edu/tuition.pdf":
        return httpx.Response(200, content=b"%PDF-1.7")
    raise AssertionError(f"unexpected request {url}")


class FakeTime:
    def __init__(self):
        self.t = 0.0
        self.slept = []

    def clock(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


@pytest.fixture
def proposed(registry):
    """Mark every fixture page as proposed so all of them are checked."""
    registry.pages["url_status"] = "proposed"
    return registry


def run(registry, pages=default_pages, seen=None):
    fake = FakeTime()

    def handler(request):
        if seen is not None:
            seen.append(request)
        if request.url.path == "/robots.txt":
            code, text = ROBOTS[request.url.host]
            return httpx.Response(code, text=text)
        return pages(request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = check_urls(registry, contact_email=EMAIL, client=client, clock=fake.clock, sleep=fake.sleep,
                        now=lambda: NOW)
    return result, fake


def by_page(result):
    return {r.page_id: r for r in result.itertuples(index=False)}


def test_columns_and_order(proposed):
    result, _ = run(proposed)
    assert list(result.columns) == COLUMNS
    assert list(result["page_id"]) == sorted(result["page_id"])
    assert set(result["checked_at"]) == {NOW}


def test_classification(proposed):
    r = by_page(run(proposed)[0])
    assert (r["pg-0001"].result, r["pg-0001"].http_status, r["pg-0001"].final_url) == (
        "redirected", "200", "https://datascience.alpha.edu/programs/ms")
    assert (r["pg-0002"].result, r["pg-0002"].http_status) == ("broken", "404")
    assert r["pg-0003"].result == "ok"                      # redirect only added a tracking parameter
    assert r["pg-0003"].final_url == "https://business.alpha.edu/msba?utm_source=redirect"
    assert (r["pg-0004"].result, r["pg-0004"].http_status, r["pg-0004"].final_url) == ("robots_disallowed", "", "")
    assert (r["pg-0005"].result, r["pg-0005"].http_status, r["pg-0005"].final_url) == ("ok", "200", "")


def test_page_bodies_are_never_read(proposed):
    # Streams that raise when read: page bodies must not be consumed; robots.txt may be.
    class Unreadable(httpx.SyncByteStream):
        def __iter__(self):
            raise AssertionError("page body was read")

    def pages(request):
        resp = default_pages(request)
        if resp.status_code == 200:
            return httpx.Response(200, stream=Unreadable())
        return resp
    result, _ = run(proposed, pages)
    assert by_page(result)["pg-0005"].result == "ok"


def test_robots_disallowed_page_is_never_requested(proposed):
    seen = []
    run(proposed, seen=seen)
    assert "https://business.alpha.edu/msba/admissions?term=fall" not in {str(r.url) for r in seen}


def test_robots_txt_read_once_per_domain(proposed):
    seen = []
    run(proposed, seen=seen)
    robots = [r.url.host for r in seen if r.url.path == "/robots.txt"]
    assert sorted(robots) == sorted(ROBOTS)


def test_robots_unavailable_is_distinct_from_disallowed(proposed):
    def handler_pages(request):
        return default_pages(request)
    fake = FakeTime()

    def handler(request):
        if request.url.path == "/robots.txt":
            if request.url.host == "grad.alpha.edu":
                return httpx.Response(403)
            code, text = ROBOTS[request.url.host]
            return httpx.Response(code, text=text)
        return handler_pages(request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = check_urls(proposed, contact_email=EMAIL, client=client, clock=fake.clock, sleep=fake.sleep,
                        now=lambda: NOW)
    r = by_page(result)
    assert r["pg-0002"].result == "robots_unavailable"
    assert r["pg-0005"].result == "robots_unavailable"
    assert r["pg-0004"].result == "robots_disallowed"


def test_robots_network_error_is_unavailable(proposed):
    fake = FakeTime()

    def handler(request):
        if request.url.path == "/robots.txt" and request.url.host == "datascience.alpha.edu":
            raise httpx.ConnectError("boom", request=request)
        if request.url.path == "/robots.txt":
            code, text = ROBOTS[request.url.host]
            return httpx.Response(code, text=text)
        return default_pages(request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = check_urls(proposed, contact_email=EMAIL, client=client, clock=fake.clock, sleep=fake.sleep,
                        now=lambda: NOW)
    assert by_page(result)["pg-0001"].result == "robots_unavailable"


def test_page_filter(proposed):
    seen = []
    fake = FakeTime()

    def handler(request):
        seen.append(str(request.url))
        if request.url.path == "/robots.txt":
            code, text = ROBOTS[request.url.host]
            return httpx.Response(code, text=text)
        return default_pages(request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = check_urls(proposed, contact_email=EMAIL, client=client, clock=fake.clock, sleep=fake.sleep,
                        now=lambda: NOW, page_ids=["pg-0005"])
    assert list(result["page_id"]) == ["pg-0005"]
    assert seen == ["https://grad.alpha.edu/robots.txt", "https://grad.alpha.edu/tuition.pdf"]


@pytest.mark.parametrize("bad", [["pg-0999"], ["pg-0001"]])
def test_page_filter_rejects_unknown_or_confirmed(registry, bad):
    # In the fixture pg-0001 is confirmed and pg-0999 does not exist.
    with pytest.raises(ValueError, match=bad[0]):
        check_urls(registry, contact_email=EMAIL, client=httpx.Client(transport=httpx.MockTransport(
            lambda r: httpx.Response(200))), page_ids=bad)


def test_merge_url_check_replaces_only_checked_rows(proposed, tmp_path):
    from gradprog.registry.url_check import merge_url_check

    full, _ = run(proposed)
    path = tmp_path / "url_check.csv"
    write_url_check(full, path)
    partial = full[full["page_id"] == "pg-0002"].copy()
    partial["result"] = "ok"
    merged = merge_url_check(path, partial)
    r = by_page(merged)
    assert r["pg-0002"].result == "ok"
    assert r["pg-0001"].result == "redirected"
    assert list(merged["page_id"]) == sorted(merged["page_id"])


def test_only_proposed_pages_are_checked(registry):
    # In the fixture only pg-0004 is proposed (and robots-disallowed: robots.txt was read and forbids it).
    seen = []
    result, _ = run(registry, seen=seen)
    assert list(result["page_id"]) == ["pg-0004"]
    assert [str(r.url) for r in seen] == ["https://business.alpha.edu/robots.txt"]


@pytest.mark.parametrize("code", [410])
def test_gone_is_broken(proposed, code):
    def pages(request):
        if str(request.url) == "https://grad.alpha.edu/tuition.pdf":
            return httpx.Response(code)
        return default_pages(request)
    assert by_page(run(proposed, pages)[0])["pg-0005"].result == "broken"


@pytest.mark.parametrize("code", [403, 500, 503])
def test_other_status_is_error(proposed, code):
    def pages(request):
        if str(request.url) == "https://grad.alpha.edu/tuition.pdf":
            return httpx.Response(code)
        return default_pages(request)
    row = by_page(run(proposed, pages)[0])["pg-0005"]
    assert (row.result, row.http_status) == ("error", str(code))


def test_network_error_is_error(proposed):
    def pages(request):
        if str(request.url) == "https://grad.alpha.edu/tuition.pdf":
            raise httpx.ConnectError("boom", request=request)
        return default_pages(request)
    row = by_page(run(proposed, pages)[0])["pg-0005"]
    assert (row.result, row.http_status) == ("error", "")


def test_redirect_loop_is_error(proposed):
    def pages(request):
        if str(request.url) == "https://grad.alpha.edu/tuition.pdf":
            return httpx.Response(302, headers={"Location": "https://grad.alpha.edu/tuition.pdf"})
        return default_pages(request)
    assert by_page(run(proposed, pages)[0])["pg-0005"].result == "error"


def test_redirect_to_http_is_redirected(proposed):
    def pages(request):
        if str(request.url) == "https://grad.alpha.edu/tuition.pdf":
            return httpx.Response(301, headers={"Location": "http://grad.alpha.edu/tuition.pdf"})
        if str(request.url) == "http://grad.alpha.edu/tuition.pdf":
            return httpx.Response(200)
        return default_pages(request)
    row = by_page(run(proposed, pages)[0])["pg-0005"]
    assert (row.result, row.final_url) == ("redirected", "http://grad.alpha.edu/tuition.pdf")


def test_user_agent_and_spacing(proposed):
    seen = []
    _, fake = run(proposed, seen=seen)
    assert {r.headers["user-agent"] for r in seen} == {user_agent(EMAIL)}
    requests = len([r for r in seen if not (r.url.path in ("/programs/ms",) or "utm_source" in str(r.url))])
    assert len(fake.slept) >= requests - 1
    assert all(s >= 3.0 for s in fake.slept)


def test_registry_is_not_modified(proposed):
    before = copy.deepcopy([proposed.programs, proposed.pages, proposed.program_pages, proposed.domains])
    run(proposed)
    after = [proposed.programs, proposed.pages, proposed.program_pages, proposed.domains]
    for a, b in zip(before, after):
        assert a.equals(b)


def test_requires_contact_email(proposed, monkeypatch):
    monkeypatch.delenv("GRADPROG_CONTACT_EMAIL", raising=False)
    with pytest.raises(DownloadError, match="GRADPROG_CONTACT_EMAIL"):
        check_urls(proposed, client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200))))


def test_write_url_check(proposed, tmp_path):
    result, _ = run(proposed)
    path = tmp_path / "url_check.csv"
    write_url_check(result, path)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == ",".join(COLUMNS)
    assert len(lines) == 1 + len(result)
