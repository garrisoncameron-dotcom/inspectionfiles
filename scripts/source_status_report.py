#!/usr/bin/env python3
"""Write a concise source status report for the Violation Desk."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from violation_desk.sources import SOURCES


OUTPUT_PATH = Path("docs/source-status-report.md")


def main() -> None:
    grouped = defaultdict(list)
    for source in SOURCES.values():
        grouped[source.status].append(source)

    lines = ["# Violation Desk Source Status", ""]
    for status in sorted(grouped):
        lines.extend([f"## {status.replace('_', ' ').title()}", ""])
        for source in sorted(grouped[status], key=lambda item: item.id):
            lines.extend(
                [
                    f"### {source.name}",
                    "",
                    f"- ID: `{source.id}`",
                    f"- Kind: `{source.kind}`",
                    f"- Agency: {source.agency}",
                    f"- Endpoint: {source.endpoint}",
                    f"- Notes: {source.notes or 'None'}",
                    "",
                ]
            )

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
