#!/usr/bin/env python3
"""Run the Inspection Files Violation Desk MVP."""

from __future__ import annotations

import argparse
from pathlib import Path

from violation_desk.fetch import fetch_records
from violation_desk.produce import score_records, write_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Inspection Files Violation Desk reports.")
    parser.add_argument(
        "--sources",
        default="nyc,chicago",
        help="Comma-separated source IDs. Available in work/violation_desk/sources.py.",
    )
    parser.add_argument("--limit-per-source", type=int, default=5000)
    parser.add_argument("--minimum-score", type=int, default=45)
    parser.add_argument("--brief-count", type=int, default=3)
    parser.add_argument(
        "--output-dir",
        default="outputs/violation-desk-mvp",
        help="Directory for generated reports.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_ids = [source.strip() for source in args.sources.split(",") if source.strip()]
    records = fetch_records(source_ids=source_ids, limit_per_source=args.limit_per_source)
    leads = score_records(records, minimum_score=args.minimum_score)
    written = write_outputs(leads, Path(args.output_dir), brief_count=args.brief_count)

    print(f"Fetched {len(records)} records from {', '.join(source_ids)}.")
    print(f"Scored {len(leads)} leads at or above {args.minimum_score}.")
    print("Wrote:")
    for path in written:
        print(f"- {path}")


if __name__ == "__main__":
    main()

