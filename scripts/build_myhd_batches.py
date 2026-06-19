#!/usr/bin/env python3
"""Build prioritized My Health Department jurisdiction batches."""

from __future__ import annotations

import json
from pathlib import Path


INPUT_PATH = Path("outputs/myhealthdepartment-jurisdictions.json")
OUTPUT_PATH = Path("outputs/myhd-priority-batches.json")


PRIORITY_TERMS = {
    "statewide": ("tennessee", "virginia", "oregon", "arizona", "soh"),
    "major_metros": (
        "tarrant",
        "fort-worth",
        "plano",
        "mecklenburg",
        "fairfax",
        "arlington",
        "alexandria",
        "virginia-beach",
        "richmond",
        "norfolk",
        "henrico",
        "loudoun",
    ),
    "west_coast": (
        "walla",
        "clallam",
        "grant-county",
        "okanogan",
        "oregon",
    ),
    "southwest": (
        "arizona",
        "apache",
        "navajo",
        "santa-cruz",
    ),
    "tourism": (
        "hawaii",
        "soh",
        "virginia-beach",
        "pueblo",
    ),
}


def score_slug(slug: str) -> int:
    score = 0
    for weight, terms in ((20, PRIORITY_TERMS["major_metros"]), (15, PRIORITY_TERMS["statewide"]), (10, PRIORITY_TERMS["tourism"]), (8, PRIORITY_TERMS["west_coast"]), (8, PRIORITY_TERMS["southwest"])):
        if any(term in slug for term in terms):
            score += weight
    if slug.startswith("va-"):
        score += 4
    if slug.startswith(("or-", "az-", "wa-")):
        score += 4
    return score


def main() -> None:
    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    jurisdictions = payload["jurisdictions"]

    ranked = sorted(
        (
            {
                **item,
                "priorityScore": score_slug(item["slug"]),
                "closureUrl": f"https://inspections.myhealthdepartment.com/{item['slug']}/restaurant-closures",
                "inspectionUrl": f"https://inspections.myhealthdepartment.com/{item['slug']}",
            }
            for item in jurisdictions
        ),
        key=lambda item: (item["priorityScore"], item["slug"]),
        reverse=True,
    )

    batches = []
    batch_size = 8
    high_priority = [item for item in ranked if item["priorityScore"] > 0]
    for index in range(0, len(high_priority), batch_size):
        batches.append(
            {
                "batch": len(batches) + 1,
                "slugs": high_priority[index : index + batch_size],
            }
        )

    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "sourceCount": len(jurisdictions),
                "prioritizedCount": len(high_priority),
                "batchSize": batch_size,
                "batches": batches,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {len(batches)} batches to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
