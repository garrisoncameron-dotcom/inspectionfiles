#!/usr/bin/env python3
"""Export current Violation Desk leads into the static dashboard data file."""

from __future__ import annotations

import json
from pathlib import Path

from violation_desk.fetch import fetch_records
from violation_desk.produce import official_record_hint, score_records
from violation_desk.scoring import extract_grossest_detail


OUTPUT_PATH = Path("data.js")
MAX_DASHBOARD_LEADS = 300


def main() -> None:
    source_ids = [
        "nyc",
        "chicago",
        "la_county_closures",
        "orange_county_closures",
        "mecklenburg_county",
        "san_francisco",
    ]
    if Path("data-snapshots/myhd-inspection-snapshots.json").exists():
        source_ids.append("myhd_inspection_snapshots")
    records = []
    active_sources = []
    failed_sources = []
    source_labels = {
        "nyc": "NYC",
        "chicago": "Chicago",
        "la_county_closures": "LA County",
        "orange_county_closures": "Orange County",
        "mecklenburg_county": "Mecklenburg County",
        "san_francisco": "San Francisco",
        "dc": "DC",
        "myhd_inspection_snapshots": "My Health Dept Snapshots",
    }

    for source_id in source_ids:
        try:
            source_records = fetch_records(source_ids=[source_id], limit_per_source=1000)
        except Exception as exc:
            failed_sources.append({"source": source_id, "error": str(exc)})
            continue
        records.extend(source_records)
        if source_records:
            active_sources.append(source_labels[source_id])

    leads = score_records(records, minimum_score=45)
    display_leads = list(leads[:80])
    seen_keys = {
        (lead.record.source_id, lead.record.establishment, lead.record.address, lead.record.inspection_date[:10])
        for lead in display_leads
    }

    for source_id in source_ids:
        source_leads = [lead for lead in leads if lead.record.source_id == source_id]
        for lead in source_leads[:30]:
            key = (lead.record.source_id, lead.record.establishment, lead.record.address, lead.record.inspection_date[:10])
            if key not in seen_keys:
                display_leads.append(lead)
                seen_keys.add(key)
            if len(display_leads) >= MAX_DASHBOARD_LEADS:
                break
        if len(display_leads) >= MAX_DASHBOARD_LEADS:
            break

    payload = {
        "generatedAt": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "leadsReviewed": len(leads),
        "activeSources": active_sources,
        "failedSources": failed_sources,
        "leads": [],
    }

    for rank, lead in enumerate(display_leads, start=1):
        record = lead.record
        scorecard = lead.scorecard
        stable_id = "|".join(
            [
                record.source_id,
                record.establishment.lower(),
                record.address.lower(),
                record.inspection_date[:10],
                str(record.raw.get("state_id", "")).lower(),
            ]
        )
        payload["leads"].append(
            {
                "id": stable_id,
                "rank": rank,
                "case": record.establishment,
                "score": lead.score,
                "section": scorecard["desk_section"],
                "violationType": scorecard["violation_type"],
                "location": record.address,
                "inspectionDate": record.inspection_date[:10],
                "agency": record.agency,
                "status": record.result_text or "Needs review",
                "officialRecord": official_record_hint(record),
                "grossestDetail": extract_grossest_detail(record.violation_text, limit=260),
                "producerRecommendation": "Full segment candidate" if lead.score >= 75 else "Quick-hit or watchlist candidate",
                "followUp": [
                    "Confirm current operating status.",
                    "Check reinspection or reopening status.",
                    "Search for local coverage or a public statement.",
                ],
            }
        )

    if failed_sources and OUTPUT_PATH.exists():
        previous = OUTPUT_PATH.read_text(encoding="utf-8")
        previous_lead_count = previous.count('"rank":')
        if previous_lead_count > len(payload["leads"]):
            print(
                f"Keeping existing dashboard data because refreshed data has "
                f"{len(payload['leads'])} leads and previous data has {previous_lead_count}."
            )
            print(f"Failed sources: {failed_sources}")
            return

    OUTPUT_PATH.write_text(
        "window.VIOLATION_DESK_DATA = " + json.dumps(payload, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(payload['leads'])} dashboard leads to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
