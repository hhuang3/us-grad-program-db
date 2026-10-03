"""Command line entry point: `uv run gradprog <command>`."""

import argparse
import sys
from pathlib import Path

from gradprog.util.download import DownloadError, Downloader, register_manual

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw"
MANIFEST = REPO / "data" / "manifest" / "manifest.csv"
REGISTRY = REPO / "data" / "registry"
CANDIDATES = REPO / "data" / "ref" / "candidates.csv"


def cmd_register_manual(args):
    path = register_manual(args.source, args.url, args.file, args.retrieved_at, args.notes, RAW, MANIFEST)
    print(f"registered {path}")


def cmd_download(args):
    from gradprog.ref.sources import DOWNLOADS

    unknown = [s for s in args.sources if s not in DOWNLOADS]
    if unknown:
        raise DownloadError(f"no automatic download for {unknown}; known: {sorted(DOWNLOADS)}")
    d = Downloader(RAW, MANIFEST)
    for source in args.sources:
        for url in DOWNLOADS[source]:
            path = d.fetch(source, url)
            print(f"{source}: {path.relative_to(REPO)} ({path.stat().st_size:,} bytes)")


def cmd_build(args):
    from gradprog.ref.build import build

    build(REPO, only=args.tables or None)


def cmd_registry(args):
    import pandas as pd

    from gradprog.registry import tables
    from gradprog.registry.robots import check_robots
    from gradprog.registry.validate import load_head_tables, validate
    from gradprog.registry.worksheet import build_worksheet, write_worksheet

    if args.registry_command == "init":
        tables.init_registry(REGISTRY)
        print(f"created empty registry tables in {REGISTRY.relative_to(REPO)}")
        return
    if args.registry_command == "worksheet":
        candidates = pd.read_csv(CANDIDATES, dtype=str, keep_default_na=False)
        path = REGISTRY / "selection_worksheet.csv"
        ws = build_worksheet(candidates)
        write_worksheet(ws, path, force=args.force)
        print(f"wrote {path.relative_to(REPO)} ({len(ws):,} rows)")
        return

    reg = tables.load_registry(REGISTRY)
    if args.registry_command == "add-page":
        from datetime import datetime, timezone

        added = args.added_at or datetime.now(timezone.utc).date().isoformat()
        pid = tables.add_page(reg, args.url, args.type, args.owner, args.format, args.program, added,
                              url_status=args.status)
        tables.save_registry(reg, REGISTRY)
        print(f"added {pid}")
    elif args.registry_command == "derive":
        tables.save_registry(tables.derive(reg), REGISTRY)
        print("recomputed derived columns")
    elif args.registry_command == "check-robots":
        check_robots(reg)
        tables.save_registry(reg, REGISTRY)
        d = reg.domains
        for row in d.itertuples(index=False):
            print(f"{row.domain}: {row.robots_status}, registered paths: {row.robots_allows_registered_paths}")
    elif args.registry_command == "check-urls":
        from collections import Counter

        from gradprog.registry.url_check import check_urls, merge_url_check, write_url_check

        result = check_urls(reg, page_ids=args.page)
        path = REGISTRY / "url_check.csv"
        write_url_check(merge_url_check(path, result) if args.page else result, path)
        print(f"wrote {path.relative_to(REPO)}: {dict(Counter(result['result']))}")
        for r in result[result["result"] != "ok"].itertuples(index=False):
            print(f"  {r.page_id} {r.result} {r.http_status} {r.final_url}")
    elif args.registry_command == "validate":
        candidates = pd.read_csv(CANDIDATES, dtype=str, keep_default_na=False)
        previous = load_head_tables(REPO)
        uc_path = REGISTRY / "url_check.csv"
        url_check = pd.read_csv(uc_path, dtype=str, keep_default_na=False) if uc_path.exists() else None
        result = validate(reg, candidates, previous=previous, ready=args.ready, batch=args.batch,
                          url_check=url_check)
        if previous is None:
            result.warnings.append("not inside a git work tree: skipped the no-deletion check")
        _print_validation(result)
        if result.errors:
            raise SystemExit(1)


def _print_validation(result):
    for e in result.errors:
        print(f"ERROR   {e}")
    for w in result.warnings:
        print(f"WARNING {w}")
    rep = result.report
    if rep:
        print("\nquota (selected / target, pilot + main):")
        for g, q in rep["quota"].items():
            print(f"  {g:<10} {q['selected']:>3} / {q['target']:<3} ({q['pilot']} + {q['main']})")
        print("status counts:", rep["status_counts"])
        print("exclusion reasons:", rep["exclusion_reasons"] or "none")
        print(f"pages shared by several programs: {rep['shared_pages']}; "
              f"graduate_school pages: {rep['graduate_school_pages']}")
        print("domains with tos_status != no_restriction:", rep["tos_not_ok_domains"] or "none")
        blocked = rep.get("ready_crawl_blocked", rep["crawl_blocked_pages"])
        label = "pilot pages not crawlable" if "ready_crawl_blocked" in rep else "pages not crawlable"
        print(f"{label}: {len(blocked)}")
        for b in blocked:
            print(f"  {b['page_id']} {b['domain']} ({b['reason']})")
        if "ready_manual_programs" in rep:
            print(f"pilot programs with fetch_method=manual: {len(rep['ready_manual_programs'])}")
            for pid in rep["ready_manual_programs"]:
                print(f"  {pid}")
    print(f"\n{len(result.errors)} error(s), {len(result.warnings)} warning(s)")


def main(argv=None):
    p = argparse.ArgumentParser(prog="gradprog")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("register-manual", help="register a manually downloaded raw file (01 §7.2)")
    r.add_argument("--source", required=True)
    r.add_argument("--url", required=True, help="official URL of the file")
    r.add_argument("--file", required=True, type=Path)
    r.add_argument("--retrieved-at", required=True, help="UTC YYYY-MM-DDTHH:MM:SSZ, or YYYY-MM-DD")
    r.add_argument("--notes", required=True)
    r.set_defaults(func=cmd_register_manual)

    d = sub.add_parser("download", help="download raw files for the given sources (01 §7.1)")
    d.add_argument("sources", nargs="+")
    d.set_defaults(func=cmd_download)

    b = sub.add_parser("build", help="parse the latest raw files into data/ref")
    b.add_argument("tables", nargs="*")
    b.set_defaults(func=cmd_build)

    reg = sub.add_parser("registry", help="Phase 2 source registry (06)")
    rsub = reg.add_subparsers(dest="registry_command", required=True)
    rsub.add_parser("init", help="create the four empty registry tables")
    w = rsub.add_parser("worksheet", help="write data/registry/selection_worksheet.csv")
    w.add_argument("--force", action="store_true", help="overwrite an existing worksheet")
    a = rsub.add_parser("add-page", help="register one page and link it to programs")
    a.add_argument("--url", required=True)
    a.add_argument("--type", required=True, help="page_type")
    a.add_argument("--owner", required=True, help="owner_level")
    a.add_argument("--format", default="html", help="content_format (html/pdf)")
    a.add_argument("--program", required=True, action="append", help="program_id; repeat for shared pages")
    a.add_argument("--status", default="proposed", help="url_status")
    a.add_argument("--added-at", help="YYYY-MM-DD (default: today, UTC)")
    rsub.add_parser("derive", help="recompute derived columns (domain, crawl_allowed)")
    rsub.add_parser("check-robots", help="check robots.txt for every domain")
    cu = rsub.add_parser("check-urls", help="status codes and redirects of proposed pages (writes url_check.csv)")
    cu.add_argument("--page", action="append", help="only check this page_id (repeatable)")
    v = rsub.add_parser("validate", help="validate the registry")
    v.add_argument("--ready", action="store_true", help="Phase 3 readiness checks")
    v.add_argument("--batch", choices=["pilot", "main"], help="batch for --ready")
    reg.set_defaults(func=cmd_registry)

    args = p.parse_args(argv)
    if getattr(args, "ready", False) and not args.batch:
        p.error("--ready requires --batch")
    try:
        args.func(args)
    except (DownloadError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
