"""Command line entry point: `uv run gradprog <command>`."""

import argparse
import sys
from pathlib import Path

from gradprog.util.download import DownloadError, Downloader, register_manual

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw"
MANIFEST = REPO / "data" / "manifest" / "manifest.csv"


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

    args = p.parse_args(argv)
    try:
        args.func(args)
    except (DownloadError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
