"""Fetch and normalize inspection records from public data portals."""

from __future__ import annotations

import json
import re
from pathlib import Path
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from html import unescape
from dataclasses import dataclass

from .sources import SOURCES, Source


@dataclass(frozen=True)
class InspectionRecord:
    source_id: str
    source_name: str
    agency: str
    establishment: str
    address: str
    inspection_date: str
    violation_text: str
    result_text: str
    raw: dict[str, object]


def fetch_source(source: Source, limit: int = 5000) -> list[dict[str, object]]:
    if source.kind in {"local_json", "myhd_snapshot"}:
        path = Path(source.endpoint)
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload.get("rows", [])[:limit]

    if source.kind == "dc_portal":
        return fetch_dc_portal(limit=limit)

    if source.kind != "socrata":
        raise ValueError(f"Source {source.id} requires a custom adapter: {source.notes}")

    params = {
        "$limit": str(limit),
        "$order": f"{source.date_field} DESC",
    }
    if source.query:
        params["$where"] = source.query

    url = f"{source.endpoint}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "InspectionFilesViolationDesk/0.1"})

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def strip_html(value: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", value)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def fetch_text(url: str, data: bytes | None = None) -> str:
    request = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def fetch_dc_portal(limit: int = 50) -> list[dict[str, object]]:
    end = datetime.now()
    start = end - timedelta(days=30)
    form = urllib.parse.urlencode(
        {
            "a": "Inspections",
            "inputEstabName": "",
            "inputPermitType": "ANY",
            "inputInspType": "ANY",
            "inputWard": "ANY",
            "inputQuad": "ANY",
            "startDate": start.strftime("%m/%d/%Y"),
            "endDate": end.strftime("%m/%d/%Y"),
            "btnSearch": "Search",
        }
    ).encode()

    html = fetch_text("https://dc.healthinspections.us/index.cfm", data=form)
    item_pattern = re.compile(r"(?is)<li>\s*<h3><a[^>]*>(.*?)</a></h3>(.*?)<div id=\"divInspectionSearchResultsListing\">(.*?)</div>\s*</li>")
    link_pattern = re.compile(r'(?is)<a href="([^"]*_paper_food_inspection_report\.cfm\?[^"]+)"[^>]*>(.*?)</a>')
    rows: list[dict[str, object]] = []

    for item in item_pattern.finditer(html):
        establishment = strip_html(item.group(1))
        details = strip_html(item.group(2))
        address = details.split("Ward:", 1)[0].strip()

        for href, label_html in link_pattern.findall(item.group(3)):
            if len(rows) >= limit:
                return rows

            report_url = urllib.parse.urljoin("https://dc.healthinspections.us/index.cfm", href)
            report_html = fetch_text(report_url)
            report_text = extract_dc_findings(strip_html(report_html))
            label = strip_html(label_html)
            date_match = re.search(r"([A-Z][a-z]+,\s+[A-Z][a-z]+\s+\d{1,2},\s+\d{4})", label)
            inspection_date = ""
            if date_match:
                try:
                    inspection_date = datetime.strptime(date_match.group(1), "%A, %B %d, %Y").strftime("%Y-%m-%dT00:00:00")
                except ValueError:
                    inspection_date = ""

            rows.append(
                {
                    "facility_name": establishment,
                    "address": address,
                    "city": "Washington",
                    "zip": "",
                    "inspection_date": inspection_date,
                    "violation_text": report_text,
                    "result": label,
                    "official_url": report_url,
                }
            )

    return rows


def extract_dc_findings(report_text: str) -> str:
    """Keep likely inspector findings and drop repeated report boilerplate."""
    findings: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", report_text):
        clean = sentence.strip()
        if not clean:
            continue
        if re.search(r"\b(observed|instructed|correct|violation|closure|rodent|roach|cockroach|dropping|vermin|mold|sewage|wastewater|no hot water|hot water|handwashing|temperature)\b", clean, re.I):
            if not re.search(r"\blicensed sewage\s*&?\s*liquid waste transport contractor\b", clean, re.I):
                findings.append(clean)
    return " ".join(findings[:80]) or report_text[:4000]


def normalize(source: Source, row: dict[str, object]) -> InspectionRecord:
    address_parts = [str(row.get(field, "")).strip() for field in source.address_fields]
    address = ", ".join(part for part in address_parts if part)

    raw_date = str(row.get(source.date_field, "")).strip()
    if source.kind in {"local_json", "myhd_snapshot"} and len(raw_date) == 10:
        raw_date = f"{raw_date}T00:00:00"

    return InspectionRecord(
        source_id=source.id,
        source_name=source.name,
        agency=source.agency,
        establishment=str(row.get(source.name_field, "")).strip() or "Unknown establishment",
        address=address,
        inspection_date=raw_date,
        violation_text=str(row.get(source.text_field, "")).strip(),
        result_text=str(row.get(source.result_field, "")).strip() if source.result_field else "",
        raw=row,
    )


def fetch_records(source_ids: list[str] | None = None, limit_per_source: int = 5000) -> list[InspectionRecord]:
    selected_ids = source_ids or [
        source_id for source_id, source in SOURCES.items() if source.status == "live"
    ]
    records: list[InspectionRecord] = []

    for source_id in selected_ids:
        source = SOURCES[source_id]
        rows = fetch_source(source, limit=limit_per_source)
        records.extend(normalize(source, row) for row in rows)

    return records
