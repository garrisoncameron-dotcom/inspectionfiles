"""Turn scored inspection records into Violation Desk producer artifacts."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .fetch import InspectionRecord
from .scoring import extract_grossest_detail, parse_date, score_text


@dataclass(frozen=True)
class Lead:
    record: InspectionRecord
    scorecard: dict[str, object]

    @property
    def score(self) -> int:
        return int(self.scorecard["score"])


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "case"


def inspector_comments(text: str) -> str:
    parts = re.split(r"\s+\|\s+", text or "")
    comments: list[str] = []

    for part in parts:
        marker = " - Comments:"
        if marker in part:
            comments.append(part.split(marker, 1)[1].strip())
        else:
            comments.append(part.strip())

    return "\n".join(comment for comment in comments if comment)


def detect_repeat_points(records: list[InspectionRecord]) -> dict[tuple[str, str], int]:
    counts = Counter((record.source_id, record.establishment.lower()) for record in records)
    return {key: min((count - 1) * 3, 10) for key, count in counts.items() if count > 1}


def aggregate_records(records: list[InspectionRecord]) -> list[InspectionRecord]:
    grouped: dict[tuple[str, str, str, str], InspectionRecord] = {}

    for record in records:
        key = (
            record.source_id,
            record.establishment.lower(),
            record.address.lower(),
            record.inspection_date[:10],
        )
        existing = grouped.get(key)
        if not existing:
            grouped[key] = record
            continue

        merged_text = existing.violation_text
        if record.violation_text and record.violation_text not in merged_text:
            merged_text = f"{merged_text}\n\n{record.violation_text}".strip()

        merged_result = existing.result_text
        if record.result_text and record.result_text not in merged_result:
            merged_result = "; ".join(part for part in (merged_result, record.result_text) if part)

        merged_raw = dict(existing.raw)
        merged_raw["merged_records"] = int(merged_raw.get("merged_records", 1)) + 1

        grouped[key] = InspectionRecord(
            source_id=existing.source_id,
            source_name=existing.source_name,
            agency=existing.agency,
            establishment=existing.establishment,
            address=existing.address,
            inspection_date=existing.inspection_date,
            violation_text=merged_text,
            result_text=merged_result,
            raw=merged_raw,
        )

    return list(grouped.values())


def score_records(records: list[InspectionRecord], minimum_score: int = 45) -> list[Lead]:
    records = aggregate_records(records)
    repeat_points = detect_repeat_points(records)
    leads: list[Lead] = []

    for record in records:
        inspection_date = parse_date(record.inspection_date)
        scoring_text = inspector_comments(record.violation_text)
        scorecard = score_text(
            scoring_text,
            result_text=record.result_text,
            inspection_date=inspection_date,
            repeat_points=repeat_points.get((record.source_id, record.establishment.lower()), 0),
        )
        if int(scorecard["score"]) >= minimum_score:
            leads.append(Lead(record=record, scorecard=scorecard))

    return sorted(leads, key=lambda lead: lead.score, reverse=True)


def official_record_hint(record: InspectionRecord) -> str:
    if record.source_id == "nyc":
        camis = record.raw.get("camis", "")
        return f"https://data.cityofnewyork.us/resource/43nn-pn8j.json?camis={camis}" if camis else record.source_name
    if record.source_id == "chicago":
        inspection_id = record.raw.get("inspection_id", "")
        return (
            "https://data.cityofchicago.org/resource/4ijn-s7e5.json"
            f"?inspection_id={inspection_id}"
            if inspection_id
            else record.source_name
        )
    if record.source_id == "dc":
        return str(record.raw.get("official_url", record.source_name))
    if record.source_id in {"myhd_inspection_snapshots", "la_county_closures", "mecklenburg_county"}:
        return str(record.raw.get("official_url", record.source_name))
    return record.source_name


def make_brief(lead: Lead) -> str:
    record = lead.record
    scorecard = lead.scorecard
    grossest = extract_grossest_detail(inspector_comments(record.violation_text))

    return f"""# THE INSPECTION FILES

## Violation Desk Brief

**Case:** {record.establishment}

**Desk Section:** {scorecard["desk_section"]}

**Location:** {record.address}

**Inspection Date:** {record.inspection_date[:10]}

**Source Agency:** {record.agency}

**Official Record:** {official_record_hint(record)}

**Violation Type:** {scorecard["violation_type"]}

**Gross Index Score:** {scorecard["score"]}

**Closure / Penalty Status:** {record.result_text or "Needs review"}

**Reinspection Status:** Needs follow-up

## What Inspectors Found

{record.violation_text}

## Grossest Official Detail

{grossest}

## Why It's a Story

This record scored strongly because it matched {", ".join(scorecard["matched_terms"]) or "serious inspection language"} and comes from an official public inspection source.

## Best Host Angle

Lead with the official inspection language, then frame the segment around what the agency documented on the inspection date and what happened afterward.

## Timeline

- {record.inspection_date[:10]}: Inspection record published by {record.agency}.
- Next step: confirm whether a reinspection occurred and whether the facility corrected the cited issue.

## Prior History

Repeat Pattern Score: {scorecard["repeat_pattern"]}/10. Review the source portal for earlier inspections before treating this as a repeat-offender story.

## Follow-Up Needed

- Confirm current operating status.
- Check for reinspection or closure release.
- Search for local coverage or a public statement.
- Consider outreach for comment before publication if this becomes a major segment.

## Legal / Verification Notes

Use inspection-date language. Attribute claims to official records. Do not imply current conditions unless current records support that.

## Producer Recommendation

{"Full segment candidate" if lead.score >= 75 else "Quick-hit or watchlist candidate"}
"""


def make_rundown(leads: list[Lead], generated_at: datetime, max_items: int = 20) -> str:
    top = leads[:max_items]
    lines = [
        "# The Inspection Files",
        "",
        "## Violation Desk Weekly Rundown",
        "",
        f"Generated: {generated_at.isoformat(timespec='seconds')}",
        "",
        f"Leads reviewed: {len(leads)} scored leads",
        "",
        "## Top Gross Index Leads",
        "",
    ]

    for index, lead in enumerate(top, start=1):
        record = lead.record
        scorecard = lead.scorecard
        lines.extend(
            [
                f"### {index}. {record.establishment}",
                "",
                f"- **Score:** {lead.score}",
                f"- **Desk Section:** {scorecard['desk_section']}",
                f"- **Violation Type:** {scorecard['violation_type']}",
                f"- **Location:** {record.address}",
                f"- **Inspection Date:** {record.inspection_date[:10]}",
                f"- **Agency:** {record.agency}",
                f"- **Status:** {record.result_text or 'Needs review'}",
                f"- **Official Record:** {official_record_hint(record)}",
                f"- **Grossest Detail:** {extract_grossest_detail(inspector_comments(record.violation_text), limit=220)}",
                "",
            ]
        )

    lines.extend(
        [
            "## Producer Notes",
            "",
            "- Treat this as a lead sheet, not a final script.",
            "- Verify reinspection and current operating status before recording.",
            "- For major names, seek comment before publication.",
            "- Keep all language anchored to official records and inspection dates.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(leads: list[Lead], output_dir: Path, brief_count: int = 3) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().astimezone()
    written: list[Path] = []

    rundown_path = output_dir / "violation-desk-weekly-rundown.md"
    rundown_path.write_text(make_rundown(leads, generated_at), encoding="utf-8")
    written.append(rundown_path)

    cases_dir = output_dir / "case-briefs"
    cases_dir.mkdir(exist_ok=True)
    for stale_brief in cases_dir.glob("*.md"):
        stale_brief.unlink()

    for index, lead in enumerate(leads[:brief_count], start=1):
        slug = slugify(f"{index}-{lead.record.establishment}-{lead.record.inspection_date[:10]}")
        path = cases_dir / f"{slug}.md"
        path.write_text(make_brief(lead), encoding="utf-8")
        written.append(path)

    return written
