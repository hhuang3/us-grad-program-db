"""docs/spec/06_source_registry.md §8: proposals, add-program, the review checklist and apply-review."""

import pandas as pd
import pytest

from gradprog.registry.batch import (
    PROPOSAL_COLUMNS, add_programs, apply_review, parse_review, read_proposals, write_review,
)
from gradprog.registry.tables import RegistryError
from gradprog.registry.validate import validate

DAY = "2026-11-22"
CS_ROWS = [
    # cip_group, rank, unitid, name, state, cip, title, stem, masters, second, nonresident, count, year
    ["cs", "1", "200010", "Kappa Institute", "TX", "11.0701", "Computer Science.", "true", "900", "0", "800", "1",
     "2023-24"],
    ["cs", "2", "200001", "Alpha University", "MA", "11.0101", "Computer and Information Sciences, General.",
     "true", "300", "0", "200", "3", "2023-24"],
]


@pytest.fixture
def candidates(registry_candidates):
    extra = pd.DataFrame(CS_ROWS, columns=registry_candidates.columns)
    return pd.concat([registry_candidates, extra], ignore_index=True)


def row(**kw):
    base = dict.fromkeys(PROPOSAL_COLUMNS, "")
    base.update(kw)
    return base


def kappa(url, page_type, owner="program", **kw):
    return row(program_id="kappa-ms-computerscience", unitid="200010", cip_code="11.0701",
               institution_name="Kappa Institute", institution_short="Kappa", program_name="MS in Computer Science",
               degree_type="ms", department="Computer Science", delivery_mode="on_campus", intake_terms="fall;spring",
               url=url, page_type=page_type, owner_level=owner, content_format="html", **kw)


def alpha_cs(url, page_type, owner="program", **kw):
    return row(program_id="alpha-ms-computerscience", unitid="200001", cip_code="11.0101",
               institution_name="Alpha University", institution_short="Alpha", program_name="MS in Computer Science",
               degree_type="ms", department="Computer Science", delivery_mode="on_campus", intake_terms="fall",
               nominated="yes", url=url, page_type=page_type, owner_level=owner, content_format="html", **kw)


@pytest.fixture
def proposals():
    return pd.DataFrame([
        kappa("https://cs.kappa.edu/ms", "program_home", tos_url="https://www.kappa.edu/terms",
              tos_hint="only privacy notices", note="STEM stated"),
        kappa("https://cs.kappa.edu/ms/admissions", "admissions"),
        kappa("https://grad.kappa.edu/tuition", "tuition", owner="graduate_school",
              tos_url="https://www.kappa.edu/terms", tos_hint="same university terms"),
        alpha_cs("https://cs.alpha.edu/ms", "program_home", tos_url="", tos_hint="no terms page found"),
        # Already registered shared graduate school page: reused, not a new page (06 §2.8).
        alpha_cs("https://grad.alpha.edu/admissions/international", "admissions", owner="graduate_school"),
        # A page added to an already registered program (the patch-up list).
        row(program_id="alpha-ms-datascience", url="https://grad.alpha.edu/tuition", page_type="tuition",
            owner_level="graduate_school", content_format="html", note="tuition page linked from the program page"),
    ], columns=PROPOSAL_COLUMNS)


def added(registry, proposals, candidates):
    return add_programs(registry, proposals, candidates, DAY)


# --- proposals file (§8.1) -------------------------------------------------------

def test_read_proposals_checks_columns(tmp_path, proposals):
    path = tmp_path / "proposals.csv"
    proposals.to_csv(path, index=False)
    assert list(read_proposals(path).columns) == PROPOSAL_COLUMNS
    proposals.drop(columns="tos_hint").to_csv(path, index=False)
    with pytest.raises(RegistryError, match="columns"):
        read_proposals(path)


# --- add-program (§8.1) ----------------------------------------------------------

def test_new_programs_are_backlog_expansion(registry, proposals, candidates):
    added(registry, proposals, candidates)
    p = registry.programs.set_index("program_id")
    for pid in ("kappa-ms-computerscience", "alpha-ms-computerscience"):
        assert p.loc[pid, "status"] == "backlog"
        assert p.loc[pid, "batch"] == "expansion"
        assert p.loc[pid, "cip_group"] == "cs"
        assert p.loc[pid, "fetch_method"] == ""
        assert p.loc[pid, "added_at"] == DAY
    assert p.loc["kappa-ms-computerscience", "intake_terms"] == "fall;spring"
    assert p.loc["kappa-ms-computerscience", "selection_note"].startswith(f"Proposed {DAY}")
    assert "STEM stated" in p.loc["kappa-ms-computerscience", "selection_note"]


def test_pages_are_proposed_and_shared_pages_reused(registry, proposals, candidates):
    before = set(registry.pages["page_id"])
    result = added(registry, proposals, candidates)
    new = registry.pages[~registry.pages["page_id"].isin(before)]
    assert len(new) == 5 and set(new["url_status"]) == {"proposed"}
    assert result.new_pages == list(new["page_id"])
    links = set(map(tuple, registry.program_pages[["program_id", "page_id"]].values.tolist()))
    assert ("alpha-ms-computerscience", "pg-0002") in links          # reused graduate school page
    assert result.reused == [("alpha-ms-computerscience", "pg-0002")]
    tuition = new[new["url"] == "https://grad.alpha.edu/tuition"]["page_id"].iloc[0]
    assert ("alpha-ms-datascience", tuition) in links
    assert result.page_additions == [("alpha-ms-datascience", tuition)]


def test_robots_domains_cover_new_pages_on_registered_domains(registry, proposals, candidates):
    # 06 §8.1: robots.txt is checked for every domain holding a new page, not only for new domains.
    result = added(registry, proposals, candidates)
    assert "grad.alpha.edu" not in result.new_domains
    assert "grad.alpha.edu" in result.robots_domains
    assert set(result.new_domains) <= set(result.robots_domains)


def test_new_domains_get_tos_url_and_hint(registry, proposals, candidates):
    result = added(registry, proposals, candidates)
    d = registry.domains.set_index("domain")
    assert result.new_domains == ["cs.alpha.edu", "cs.kappa.edu", "grad.kappa.edu"]
    assert d.loc["cs.kappa.edu", "tos_url"] == "https://www.kappa.edu/terms"
    assert d.loc["cs.kappa.edu", "tos_status"] == "not_checked"
    assert d.loc["cs.kappa.edu", "tos_note"] == "Claude: only privacy notices"
    assert d.loc["cs.alpha.edu", "tos_note"] == "Claude: no terms page found"
    assert d.loc["grad.alpha.edu", "tos_status"] == "no_restriction"  # existing domain untouched


def test_result_passes_validation(registry, proposals, candidates):
    added(registry, proposals, candidates)
    assert validate(registry, candidates).errors == []


def test_rerun_skips_registered_rows(registry, proposals, candidates):
    added(registry, proposals, candidates)
    sizes = (len(registry.programs), len(registry.pages), len(registry.program_pages))
    again = added(registry, proposals, candidates)
    assert (len(registry.programs), len(registry.pages), len(registry.program_pages)) == sizes
    assert again.new_programs == [] and again.new_pages == []


def test_any_bad_row_rejects_the_whole_batch(registry, proposals, candidates):
    bad = proposals.copy()
    bad.loc[1, "page_type"] = "brochure"
    bad.loc[3, "cip_code"] = "30.7001"            # Alpha is not a cs candidate under 30.7001
    before = (len(registry.programs), len(registry.pages), len(registry.domains))
    with pytest.raises(RegistryError) as exc:
        added(registry, bad, candidates)
    assert "brochure" in str(exc.value) and "alpha-ms-computerscience" in str(exc.value)
    assert (len(registry.programs), len(registry.pages), len(registry.domains)) == before


def test_program_columns_must_agree_within_a_program(registry, proposals, candidates):
    bad = proposals.copy()
    bad.loc[1, "program_name"] = "MS in CS"
    with pytest.raises(RegistryError, match="kappa-ms-computerscience"):
        added(registry, bad, candidates)


def test_page_addition_must_match_registered_program(registry, proposals, candidates):
    bad = proposals.copy()
    bad.loc[5, "unitid"] = "200006"
    with pytest.raises(RegistryError, match="alpha-ms-datascience"):
        added(registry, bad, candidates)


def test_new_program_needs_a_known_group(registry, proposals, candidates):
    bad = proposals.copy()
    bad.loc[0:2, "unitid"] = "299999"
    with pytest.raises(RegistryError, match="299999"):
        added(registry, bad, candidates)


# --- review checklist (§8.2) -----------------------------------------------------

@pytest.fixture
def review(registry, proposals, candidates):
    added(registry, proposals, candidates)
    url_check = pd.DataFrame([["pg-0007", "https://cs.kappa.edu/ms", "ok", "200", "", DAY]],
                             columns=["page_id", "url", "result", "http_status", "final_url", "checked_at"])
    return write_review(registry, candidates, proposals, url_check, DAY, title="第一轮：cs")


def test_review_sections(review):
    assert "## 新域名条款" in review
    assert "#### 域名 cs.kappa.edu" in review and "Claude 初步判断：only privacy notices" in review
    assert "## 组 cs" in review and "名额 15" in review
    assert "我要加的学校：" in review
    # nominated programs are listed apart from those chosen by ranking (§2.8)
    assert review.index("### 点名") < review.index("#### 项目 alpha-ms-computerscience")
    assert review.index("### 按排序") < review.index("#### 项目 kappa-ms-computerscience")
    assert "#### 页面 " in review and "alpha-ms-datascience" in review
    assert "## 汇总" in review


def test_review_program_details(review):
    block = review.split("#### 项目 kappa-ms-computerscience")[1].split("####")[0]
    assert "11.0701" in block and "800" in block and "900" in block and "STEM：是" in block
    assert "工作表排名 1" in block
    assert "https://cs.kappa.edu/ms" in block and "网址检查 ok" in block
    assert "沿用" not in block
    assert block.count("决定：") == 1 and block.count("用时（分钟）：") == 1
    alpha = review.split("#### 项目 alpha-ms-computerscience")[1].split("####")[0]
    assert "pg-0002" in alpha and "沿用" in alpha


def test_review_is_parseable_when_blank(review):
    parsed = parse_review(review)
    assert parsed.programs == {}
    assert parsed.pages == {}
    assert parsed.tos == {}
    assert parsed.nominated == {"cs": ""}


def fill(review, repl):
    for old, new in repl:
        assert old in review, old
        review = review.replace(old, new, 1)
    return review


def decide(review, page_id):
    def after(head, line, value):
        i = review.index(head)
        j = review.index(line, i)
        return review[:j] + line + value + review[j + len(line):]

    review = after("#### 域名 cs.kappa.edu", "条款：", "no_restriction 只有隐私声明")
    review = after("#### 域名 grad.kappa.edu", "条款：", "no_restriction")
    review = after("#### 域名 cs.alpha.edu", "条款：", "unclear 没有条款页")
    review = after("#### 项目 kappa-ms-computerscience", "决定：", "select")
    review = after("#### 项目 kappa-ms-computerscience", "用时（分钟）：", "6")
    review = after("#### 项目 alpha-ms-computerscience", "决定：", "exclude online_only 只有线上")
    review = after("#### 项目 alpha-ms-computerscience", "用时（分钟）：", "4")
    review = after(f"#### 页面 {page_id}", "决定：", "confirm")
    review = after("## 组 cs", "我要加的学校：", "Lambda Tech, Mu College")
    return review


def tuition_page(registry):
    return registry.pages.loc[registry.pages["url"] == "https://grad.alpha.edu/tuition", "page_id"].iloc[0]


def test_parse_review(registry, review):
    parsed = parse_review(decide(review, tuition_page(registry)))
    assert parsed.programs == {"kappa-ms-computerscience": ("select", "", 6.0),
                               "alpha-ms-computerscience": ("exclude", "online_only 只有线上", 4.0)}
    assert parsed.tos["cs.kappa.edu"] == ("no_restriction", "只有隐私声明")
    assert parsed.tos["cs.alpha.edu"] == ("unclear", "没有条款页")
    assert parsed.pages == {tuition_page(registry): "confirm"}
    assert parsed.nominated == {"cs": "Lambda Tech, Mu College"}


def test_parse_review_rejects_unknown_decisions(review):
    bad = review.replace("\n决定：", "\n决定：maybe", 1)
    with pytest.raises(RegistryError, match="maybe"):
        parse_review(bad)


# --- apply-review (§8.3) ---------------------------------------------------------

def test_apply_review(registry, review, candidates):
    page = tuition_page(registry)
    summary = apply_review(registry, parse_review(decide(review, page)), url_check=None, on=DAY)
    p = registry.programs.set_index("program_id")
    k = p.loc["kappa-ms-computerscience"]
    assert k["status"] == "selected" and k["fetch_method"] == "manual"   # robots not checked yet in this registry
    a = p.loc["alpha-ms-computerscience"]
    assert a["status"] == "excluded" and a["exclusion_reason"] == "online_only"
    assert "只有线上" in a["selection_note"]
    pages = registry.pages.set_index("page_id")
    kappa_pages = registry.program_pages.loc[registry.program_pages["program_id"] == "kappa-ms-computerscience",
                                             "page_id"]
    assert set(pages.loc[kappa_pages, "url_status"]) == {"confirmed"}
    alpha_new = registry.pages.loc[registry.pages["url"] == "https://cs.alpha.edu/ms", "page_id"].iloc[0]
    assert pages.loc[alpha_new, "url_status"] == "proposed"          # excluded program's page stays proposed
    assert pages.loc[page, "url_status"] == "confirmed"
    d = registry.domains.set_index("domain")
    assert d.loc["cs.kappa.edu", "tos_status"] == "no_restriction"
    assert d.loc["cs.kappa.edu", "tos_note"] == "负责人: 只有隐私声明；Claude: only privacy notices"
    assert summary["minutes"] == {"programs": 2, "total": 10.0, "mean": 5.0}
    assert summary["nominated"] == {"cs": "Lambda Tech, Mu College"}
    assert validate(registry, candidates).errors == []


@pytest.fixture
def robots_checked(registry, proposals, candidates):
    """Registry after add-program with robots verdicts filled in as check-robots would."""
    added(registry, proposals, candidates)
    registry.pages.loc[registry.pages["url_status"] == "proposed", "robots_allowed"] = "yes"
    registry.domains.loc[registry.domains["robots_status"] == "", "robots_status"] = "fetched"
    return registry


def test_fetch_method_manual_when_any_page_is_not_crawlable(robots_checked, proposals, candidates):
    registry = robots_checked
    text = decide(write_review(registry, candidates, proposals, None, DAY), tuition_page(registry))
    # grad.kappa.edu's terms forbid automated access → the tuition page must be saved by hand
    head = text.index("#### 域名 grad.kappa.edu")
    line = text.index("条款：no_restriction", head)
    text = text[:line] + "条款：prohibits_automated_access" + text[line + len("条款：no_restriction"):]
    summary = apply_review(registry, parse_review(text), url_check=None, on=DAY)
    assert registry.programs.set_index("program_id").loc["kappa-ms-computerscience", "fetch_method"] == "manual"
    assert summary["manual_pages"] == {"nominated": {"manual": 0, "total": 0}, "ranked": {"manual": 1, "total": 3}}


def test_fetch_method_manual_when_site_returns_403(robots_checked, proposals, candidates):
    registry = robots_checked
    home = registry.pages.loc[registry.pages["url"] == "https://cs.kappa.edu/ms", "page_id"].iloc[0]
    url_check = pd.DataFrame([[home, "https://cs.kappa.edu/ms", "error", "403", "", DAY]],
                             columns=["page_id", "url", "result", "http_status", "final_url", "checked_at"])
    text = decide(write_review(registry, candidates, proposals, url_check, DAY), tuition_page(registry))
    apply_review(registry, parse_review(text), url_check=url_check, on=DAY)
    assert registry.programs.set_index("program_id").loc["kappa-ms-computerscience", "fetch_method"] == "manual"


def test_fetch_method_manual_when_site_serves_a_javascript_challenge(robots_checked, proposals, candidates):
    registry = robots_checked
    home = registry.pages.loc[registry.pages["url"] == "https://cs.kappa.edu/ms", "page_id"].iloc[0]
    url_check = pd.DataFrame([[home, "https://cs.kappa.edu/ms", "redirected", "202",
                               "https://cs.kappa.edu/ms?challenge=abc", DAY]],
                             columns=["page_id", "url", "result", "http_status", "final_url", "checked_at"])
    text = decide(write_review(registry, candidates, proposals, url_check, DAY), tuition_page(registry))
    summary = apply_review(registry, parse_review(text), url_check=url_check, on=DAY)
    assert registry.programs.set_index("program_id").loc["kappa-ms-computerscience", "fetch_method"] == "manual"
    assert summary["manual_pages"]["ranked"] == {"manual": 1, "total": 3}


def test_reject_removes_a_proposed_page(registry, review):
    page = tuition_page(registry)
    text = decide(review, page)
    i = text.index(f"#### 页面 {page}")
    j = text.index("决定：confirm", i)
    text = text[:j] + "决定：reject" + text[j + len("决定：confirm"):]
    apply_review(registry, parse_review(text), url_check=None, on=DAY)
    assert page not in set(registry.pages["page_id"])
    assert page not in set(registry.program_pages["page_id"])


def test_undecided_items_are_listed(registry, review):
    summary = apply_review(registry, parse_review(review), url_check=None, on=DAY)
    assert set(summary["undecided"]) >= {"kappa-ms-computerscience", "alpha-ms-computerscience"}
    assert registry.programs.set_index("program_id").loc["kappa-ms-computerscience", "status"] == "backlog"


def test_select_needs_every_domain_tos_decided(registry, review):
    # Selecting a program whose domain terms were left blank is allowed; its pages count as not crawlable.
    text = review
    i = text.index("#### 项目 kappa-ms-computerscience")
    j = text.index("决定：", i)
    text = text[:j] + "决定：select" + text[j + len("决定："):]
    apply_review(registry, parse_review(text), url_check=None, on=DAY)
    assert registry.programs.set_index("program_id").loc["kappa-ms-computerscience", "fetch_method"] == "manual"


def test_fetch_method_auto_when_every_page_is_crawlable(robots_checked, proposals, candidates):
    registry = robots_checked
    text = decide(write_review(registry, candidates, proposals, None, DAY), tuition_page(registry))
    summary = apply_review(registry, parse_review(text), url_check=None, on=DAY)
    assert registry.programs.set_index("program_id").loc["kappa-ms-computerscience", "fetch_method"] == "auto"
    assert summary["manual_pages"]["ranked"] == {"manual": 0, "total": 3}


def test_review_summary_projects_manual_share(robots_checked, proposals, candidates):
    # With terms not yet judged every page counts as manual; the summary also shows the share if they all pass.
    review = write_review(robots_checked, candidates, proposals, None, DAY)
    summary = review.split("## 汇总")[1]
    # 06 §2.8: the 30% cap applies to the half chosen by ranking; nominated programs are counted apart.
    ranked = summary.split("按排序：")[1].split("\n")[0]
    assert "页面 3 个" in ranked and "不能自动抓取 3 个（100%" in ranked and "上限 30%" in ranked
    assert "若条款都判为 no_restriction：0 个（0%）" in ranked
    nominated = summary.split("点名：")[1].split("\n")[0]
    assert "页面 2 个" in nominated and "不受比例限制" in nominated
