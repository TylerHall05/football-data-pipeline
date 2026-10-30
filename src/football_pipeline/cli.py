"""Command-line interface: ``football-pipeline run`` and friends."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from football_pipeline.config import LEAGUES, recent_seasons
from football_pipeline.db import apply_schema, connect
from football_pipeline.pipeline import RunSummary, run_all
from football_pipeline.sample_data import write_sample_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="football-pipeline", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="create or update the database schema")

    run = sub.add_parser("run", help="extract, clean and load match data")
    run.add_argument(
        "--leagues",
        nargs="+",
        default=["E0"],
        metavar="CODE",
        help=f"league codes (default: E0). Known: {', '.join(LEAGUES)}",
    )
    group = run.add_mutually_exclusive_group()
    group.add_argument("--seasons", nargs="+", metavar="YYZZ", help="season codes, e.g. 2425")
    group.add_argument(
        "--recent", type=int, default=3, metavar="N", help="the N most recent seasons (default: 3)"
    )
    run.add_argument("--raw-dir", default="data/raw", help="where raw CSVs are cached")
    run.add_argument("--offline", action="store_true", help="read only from the raw cache")

    sample = sub.add_parser(
        "sample-data", help="write SYNTHETIC season CSVs to the raw cache (for offline demos)"
    )
    sample.add_argument("--leagues", nargs="+", default=["E0"], metavar="CODE")
    sample.add_argument("--seasons", nargs="+", metavar="YYZZ", help="default: 3 most recent")
    sample.add_argument("--raw-dir", default="data/raw")
    sample.add_argument("--seed", type=int, default=0)
    return parser


def format_summary(summaries: Sequence[RunSummary]) -> str:
    lines = [
        f"{'league':<7}{'season':<8}{'status':<11}{'rows':>6}{'rejected':>10}"
        f"{'dupes':>7}{'new':>6}{'upd':>6}"
    ]
    for s in summaries:
        new = s.load.inserted if s.load else 0
        updated = s.load.updated if s.load else 0
        lines.append(
            f"{s.league_code:<7}{s.season:<8}{s.status:<11}{s.extracted:>6}{s.rejected:>10}"
            f"{s.duplicates:>7}{new:>6}{updated:>6}"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.command == "init-db":
        with connect() as conn:
            for name in apply_schema(conn):
                print(f"applied {name}")
        return 0

    if args.command == "sample-data":
        seasons = args.seasons or recent_seasons(3)
        for path in write_sample_files(args.leagues, seasons, args.raw_dir, args.seed):
            print(f"wrote {path} (synthetic)")
        return 0

    unknown = [code for code in args.leagues if code not in LEAGUES]
    if unknown:
        print(f"Unknown league code(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    seasons = args.seasons or recent_seasons(args.recent)
    with connect() as conn:
        summaries = run_all(conn, args.leagues, seasons, args.raw_dir, offline=args.offline)
    print(format_summary(summaries))
    return 1 if any(s.status == "failed" for s in summaries) else 0


if __name__ == "__main__":
    sys.exit(main())
