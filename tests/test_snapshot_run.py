"""docs/spec/07_snapshots.md §5.1, §7, §9: automatic snapshot runs (offline, httpx.MockTransport)."""

import copy
import itertools

import httpx
import pytest

from gradprog.snapshot.fetch import run_auto
from gradprog.snapshot.store import SnapshotStore
from gradprog.util.download import DownloadError, user_agent
from helpers import make_pdf

EMAIL = "someone@example.com"
T = {"char_drop": 0.5, "min_similarity": 0.3}
KEYWORDS = ["admission", "apply", "deadline", "requirement", "tuition", "cost", "fee", "faq", "international",
            "i-20", "visa"]
SECRET = "BODY-SENTINEL-TEXT"

URLS = {
    "pg-0001": "https://datascience.alpha.edu/ms",
    "pg-0002": "https://grad.alpha.edu/admissions/international",
    "pg-0003": "https://business.alpha.edu/msba",
    "pg-0004": "https://business.alpha.edu/msba/admissions?term=fall",
    "pg-0005": "https://grad.alpha.edu/tuition.pdf",
}
ROBOTS_OK = "User-agent: *\nDisallow:\n"


def page_html(title, extra=""):
    lines = "".join(f"<p>{title} paragraph {i} about the program.</p>" for i in range(12))
    return (f"<html><body><main><h1>{title}</h1>{lines}<p>{SECRET}</p>{extra}"
            '<a href="/ms/apply">Apply now</a> <a href="https://grad.alpha.edu/admissions/international">'
            'International admissions</a> <a href="https://gsas.alpha.edu/deadlines">Deadlines</a> '
            '<a href="https://other.edu/apply">Apply elsewhere</a> <a href="/ms/people">People</a> '
            '<a href="mailto:x@alpha.edu">Email admission</a></main></body></html>')


def html(text, status=200):
    return httpx.Response(status, headers={"content-type": "text/html; charset=utf-8"}, content=text.encode())


def default_pages():
    return {
        URLS["pg-0001"]: html(page_html("Data Science")),
        URLS["pg-0002"]: html(page_html("International admissions")),
        URLS["pg-0003"]: html(page_html("Business Analytics")),
        URLS["pg-0004"]: html(page_html("BA admissions")),
        URLS["pg-0005"]: httpx.Response(200, headers={"content-type": "application/pdf"},
                                        content=make_pdf(["Tuition per credit: $1,800", "Fees: $500"])),
    }


@pytest.fixture
def crawlable(registry):
    """Fixture registry with every page crawlable and both programs fetched automatically."""
    registry.domains["tos_status"] = "no_restriction"
    registry.pages["robots_allowed"] = "yes"
    registry.pages["crawl_allowed"] = "true"
    return registry


class Env:
    def __init__(self, registry, tmp_path):
        self.registry, self.store = registry, SnapshotStore(tmp_path / "snapshots")
        self.t, self.slept, self.seen = 0.0, [], []
        self.ticks = itertools.count()

    def now(self):
        n = next(self.ticks)  # one second per call keeps snapshot ids unique and increasing
        return f"2026-10-05T{7 + n // 3600:02d}:{n // 60 % 60:02d}:{n % 60:02d}Z"

    def run(self, pages=None, robots=None, **kw):
        pages = default_pages() if pages is None else pages
        robots = robots or {}

        def handler(request):
            self.seen.append(request)
            url = str(request.url)
            if request.url.path == "/robots.txt":
                r = robots.get(request.url.host, (200, ROBOTS_OK))
                return httpx.Response(r[0], text=r[1])
            resp = pages[url]
            if isinstance(resp, Exception):
                raise resp
            if callable(resp):
                return resp(request)
            return resp

        def clock():
            return self.t

        def sleep(s):
            self.slept.append(s)
            self.t += s

        client = httpx.Client(transport=httpx.MockTransport(handler))
        kw.setdefault("thresholds", T)
        kw.setdefault("rules", {})
        kw.setdefault("keywords", KEYWORDS)
        return run_auto(self.registry, self.store, contact_email=EMAIL, client=client, clock=clock, sleep=sleep,
                        now=self.now, **kw)

    def rows(self):
        return self.store.read_index()

    def latest(self, page_id):
        ix = self.rows()
        return ix[ix["page_id"] == page_id].iloc[-1]


@pytest.fixture
def env(crawlable, tmp_path):
    return Env(crawlable, tmp_path)


# --- first run and storage ----------------------------------------------------

def test_first_run_captures_every_auto_page(env):
    env.run()
    ix = env.rows()
    assert sorted(ix["page_id"]) == sorted(URLS)
    assert set(ix["classification"]) == {"first_capture"}
    assert set(ix["method"]) == {"auto"} and set(ix["normalizer_version"]) == {"1"}
    assert ix["run_id"].nunique() == 1 and ix["run_id"].iloc[0].endswith("-auto")
    r = env.latest("pg-0005")
    assert (r.content_type, r.http_status, r.final_url) == ("pdf", "200", URLS["pg-0005"])
    for row in ix.itertuples(index=False):
        ext = row.content_type
        assert env.store.raw_path(row.page_id, row.snapshot_id, ext).is_file()
        assert env.store.norm_path(row.page_id, row.snapshot_id, 1).is_file()
        assert row.prev_snapshot_id == ""


def test_runs_csv_row(env):
    env.run()
    runs = env.store.read_runs()
    assert len(runs) == 1
    r = runs.iloc[0]
    assert (r["method"], r["first_capture"], r["changed"], r["anomaly_page_ids"]) == ("auto", "5", "0", "")


def test_second_run_unchanged(env):
    env.run()
    env.run()
    r = env.latest("pg-0001")
    assert r.classification == "unchanged"
    first = env.rows()[env.rows()["page_id"] == "pg-0001"].iloc[0]
    assert r.prev_snapshot_id == first.snapshot_id
    assert env.rows()["run_id"].nunique() == 2


def test_changed_writes_diff_and_counts(env):
    env.run()
    pages = default_pages()
    pages[URLS["pg-0001"]] = html(page_html("Data Science", extra="<p>New deadline: January 10.</p>"))
    env.run(pages)
    r = env.latest("pg-0001")
    assert (r.classification, r.added_lines, r.removed_lines) == ("changed", "1", "0")
    assert env.store.diff_path("pg-0001", r.snapshot_id, 1).is_file()


def test_suspected_redesign(env):
    env.run()
    pages = default_pages()
    pages[URLS["pg-0001"]] = html("<html><body><p>We have moved.</p></body></html>")
    env.run(pages)
    assert env.latest("pg-0001").classification == "suspected_redesign"
    assert "pg-0001" in env.store.read_runs().iloc[-1]["anomaly_page_ids"].split(";")


# --- fetch outcomes -----------------------------------------------------------

def test_ordinary_redirect_is_classified_by_content(env):
    pages = default_pages()
    pages[URLS["pg-0002"]] = httpx.Response(301, headers={"location": "https://grad.alpha.edu/admissions/intl"})
    pages["https://grad.alpha.edu/admissions/intl"] = html(page_html("International admissions"))
    env.run(pages)
    r = env.latest("pg-0002")
    assert (r.classification, r.final_url) == ("first_capture", "https://grad.alpha.edu/admissions/intl")
    assert "redirected" in r.note


def test_redirect_to_other_page_is_unavailable(env):
    pages = default_pages()
    pages[URLS["pg-0002"]] = httpx.Response(302, headers={"location": "https://grad.alpha.edu/"})
    pages["https://grad.alpha.edu/"] = html(page_html("Home"))
    env.run(pages)
    r = env.latest("pg-0002")
    assert (r.classification, r.final_url) == ("unavailable", "https://grad.alpha.edu/")


@pytest.mark.parametrize("code, cls", [(404, "unavailable"), (410, "unavailable"), (401, "blocked"),
                                       (403, "blocked"), (500, "fetch_error"), (503, "fetch_error"),
                                       (418, "fetch_error")])
def test_status_codes(env, code, cls):
    pages = default_pages()
    pages[URLS["pg-0002"]] = html("<p>error page</p>", status=code)
    env.run(pages)
    r = env.latest("pg-0002")
    assert (r.classification, r.http_status, r.raw_sha256, r.norm_sha256) == (cls, str(code), "", "")
    assert not list((env.store.root / "raw").glob("pg-0002/*"))


@pytest.mark.parametrize("exc", [httpx.ReadTimeout("timeout"), httpx.ConnectError("refused")])
def test_network_errors(env, exc):
    pages = default_pages()
    pages[URLS["pg-0002"]] = exc
    env.run(pages)
    r = env.latest("pg-0002")
    assert (r.classification, r.http_status) == ("fetch_error", "")


def test_oversize_response(env):
    pages = default_pages()
    pages[URLS["pg-0002"]] = html("<p>" + "x" * 5000 + "</p>")
    env.run(pages, max_bytes=1000)
    r = env.latest("pg-0002")
    assert r.classification == "fetch_error" and r.raw_sha256 == ""
    assert not list((env.store.root / "raw").glob("pg-0002/*"))


def test_unsupported_content_type(env):
    pages = default_pages()
    pages[URLS["pg-0002"]] = httpx.Response(200, headers={"content-type": "image/png"}, content=b"\x89PNG")
    env.run(pages)
    assert env.latest("pg-0002").classification == "fetch_error"


def test_pdf_detected_by_magic_bytes(env):
    pages = default_pages()
    pages[URLS["pg-0005"]] = httpx.Response(200, headers={"content-type": "application/octet-stream"},
                                            content=make_pdf(["Tuition"]))
    env.run(pages)
    r = env.latest("pg-0005")
    assert (r.classification, r.content_type) == ("first_capture", "pdf")


def test_empty_text_needs_javascript(env):
    pages = default_pages()
    pages[URLS["pg-0002"]] = html("<html><body><div id='app'></div><script>render()</script></body></html>")
    env.run(pages)
    r = env.latest("pg-0002")
    assert r.classification == "fetch_error"
    assert "可能需要 JavaScript 渲染" in r.note


# --- robots.txt at run time ---------------------------------------------------

def test_robots_now_disallows(env):
    env.run(robots={"business.alpha.edu": (200, "User-agent: *\nDisallow: /msba\n")})
    assert env.latest("pg-0003").classification == "blocked"
    assert env.latest("pg-0004").classification == "blocked"
    requested = {str(r.url) for r in env.seen}
    assert URLS["pg-0003"] not in requested and URLS["pg-0004"] not in requested


def test_robots_unreadable_blocks_domain(env):
    env.run(robots={"grad.alpha.edu": (503, "")})
    assert env.latest("pg-0002").classification == "blocked"
    assert env.latest("pg-0005").classification == "blocked"


def test_robots_read_once_per_domain(env):
    env.run()
    robots = [r.url.host for r in env.seen if r.url.path == "/robots.txt"]
    assert sorted(robots) == sorted({"datascience.alpha.edu", "grad.alpha.edu", "business.alpha.edu"})


# --- options, politeness, side effects ----------------------------------------

def test_page_filter(env):
    env.run(page_ids=["pg-0002"])
    assert list(env.rows()["page_id"]) == ["pg-0002"]
    assert {str(r.url) for r in env.seen if r.url.path != "/robots.txt"} == {URLS["pg-0002"]}


def test_page_filter_rejects_non_auto_page(env):
    env.registry.pages.loc[env.registry.pages.page_id == "pg-0005", "crawl_allowed"] = "false"
    with pytest.raises(ValueError, match="pg-0005"):
        env.run(page_ids=["pg-0005"])


def test_dry_run(env):
    result = env.run(dry_run=True)
    assert env.seen == []
    assert not (env.store.root / "index.csv").exists() and not (env.store.root / "runs.csv").exists()
    assert sorted(p["page_id"] for p in result.planned) == sorted(URLS)
    assert {p["robots_url"] for p in result.planned} >= {"https://grad.alpha.edu/robots.txt"}


def test_user_agent_and_spacing(env):
    env.run()
    assert {r.headers["user-agent"] for r in env.seen} == {user_agent(EMAIL)}
    assert len(env.slept) == len(env.seen) - 1 and all(s >= 3.0 for s in env.slept)


def test_registry_not_modified(env):
    before = copy.deepcopy([env.registry.programs, env.registry.pages, env.registry.domains])
    env.run(robots={"business.alpha.edu": (200, "User-agent: *\nDisallow: /\n")})
    for a, b in zip(before, [env.registry.programs, env.registry.pages, env.registry.domains]):
        assert a.equals(b)


def test_requires_contact_email(crawlable, tmp_path, monkeypatch):
    monkeypatch.delenv("GRADPROG_CONTACT_EMAIL", raising=False)
    with pytest.raises(DownloadError, match="GRADPROG_CONTACT_EMAIL"):
        run_auto(crawlable, SnapshotStore(tmp_path), client=httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(200))), thresholds=T, rules={}, keywords=KEYWORDS)


# --- report (§9) and link discovery (§8) --------------------------------------

def test_report_has_no_page_text(env):
    result = env.run()
    text = result.report_path.read_text(encoding="utf-8")
    assert result.report_path.parent == env.store.root / "reports"
    assert SECRET not in text and "paragraph" not in text
    assert "first_capture" in text


def test_report_lists_link_candidates(env):
    result = env.run()
    urls = {c["url"] for c in result.link_candidates}
    assert "https://datascience.alpha.edu/ms/apply" in urls            # same host, keyword, not registered
    assert "https://gsas.alpha.edu/deadlines" in urls                  # other subdomain of alpha.edu
    assert "https://grad.alpha.edu/admissions/international" not in urls  # already registered
    assert "https://other.edu/apply" not in urls                       # other university
    assert "https://datascience.alpha.edu/ms/people" not in urls       # no keyword
    assert "https://datascience.alpha.edu/ms/apply" in result.report_path.read_text(encoding="utf-8")


def test_fetch_error_needs_action_only_on_second_consecutive_run(env):
    pages = default_pages()
    pages[URLS["pg-0002"]] = html("<p>x</p>", status=500)
    first = env.run(pages)
    assert [a["page_id"] for a in first.anomalies if a["needs_action"]] == []
    second = env.run(pages)
    assert [a["page_id"] for a in second.anomalies if a["needs_action"]] == ["pg-0002"]


def test_report_lists_pages_not_included(env):
    env.registry.pages.loc[env.registry.pages.page_id == "pg-0005", "crawl_allowed"] = "false"
    result = env.run()
    assert [p["page_id"] for p in result.not_included] == ["pg-0005"]
    assert "pg-0005" in result.report_path.read_text(encoding="utf-8")
