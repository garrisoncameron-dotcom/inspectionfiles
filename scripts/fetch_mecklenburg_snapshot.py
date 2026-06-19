#!/usr/bin/env python3
"""Capture Mecklenburg County restaurant inspection details for the dashboard."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from html import unescape
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener


BASE_URL = "https://public.cdpehs.com/NCENVPBL/ESTABLISHMENT/ShowESTABLISHMENTTablePage.aspx?ESTTST_CTY=60"
OUTPUT_PATH = Path("data-snapshots/mecklenburg-county-inspections.json")
MAX_DETAILS = 180
LOOKBACK_DAYS = 45


class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.inputs: list[tuple[str, str]] = []
        self.selects: list[dict[str, str | None]] = []
        self.current_select: dict[str, str | None] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag == "input" and attributes.get("name"):
            self.inputs.append((attributes["name"], attributes.get("value", "")))
        if tag == "select" and attributes.get("name"):
            self.current_select = {"name": attributes["name"], "value": None}
            self.selects.append(self.current_select)
        if tag == "option" and self.current_select is not None:
            if "selected" in attributes or self.current_select["value"] is None:
                self.current_select["value"] = attributes.get("value", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "select":
            self.current_select = None


@dataclass(frozen=True)
class SearchSpec:
    label: str
    grade: str = "--ANY--"
    page_size: str = "100"


def clean_html(value: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", value)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text).replace("\xa0", " ")
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


def form_fields(page: str) -> dict[str, str]:
    parser = FormParser()
    parser.feed(page)
    fields = {key: value for key, value in parser.inputs}
    for select in parser.selects:
        fields[str(select["name"])] = str(select["value"] or "")
    return fields


def fetch_page(opener, data: dict[str, str] | None = None) -> str:
    encoded = urlencode(data).encode() if data is not None else None
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    request = Request(BASE_URL, data=encoded, headers=headers)
    with opener.open(request, timeout=45) as response:
        return response.read().decode("utf-8", "ignore")


def search_page(opener, base_page: str, spec: SearchSpec) -> str:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)
    fields = form_fields(base_page)
    fields["ctl00$PageContent$EST_TYPE_IDFilter"] = "1"
    fields["ctl00$PageContent$GRADEFilter"] = spec.grade
    fields["ctl00$PageContent$INSPECTION_DATEFromFilter"] = start_date.strftime("%-m/%-d/%Y")
    fields["ctl00$PageContent$INSPECTION_DATEToFilter"] = end_date.strftime("%-m/%-d/%Y")
    fields["__EVENTTARGET"] = "ctl00$PageContent$FilterButton$_Button"
    fields["__EVENTARGUMENT"] = ""
    page = fetch_page(opener, fields)

    fields = form_fields(page)
    fields["ctl00$PageContent$Pagination$_PageSize"] = spec.page_size
    fields["__EVENTTARGET"] = "ctl00$PageContent$Pagination$_PageSizeButton"
    fields["__EVENTARGUMENT"] = ""
    return fetch_page(opener, fields)


def parse_list_rows(page: str, search_label: str) -> list[dict[str, str]]:
    row_pattern = re.compile(
        r'<tr><td id="ctl00_PageContent_VW_PUBLIC_ESTINSPTableControlRepeater_(ctl\d+)_ViolDtlRow".*?</tr>',
        re.S,
    )
    rows: list[dict[str, str]] = []
    for match in row_pattern.finditer(page):
        row_html = match.group(0)
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)
        if len(cells) < 10:
            continue
        values = [clean_html(cell) for cell in cells]
        rows.append(
            {
                "search_label": search_label,
                "row_control": match.group(1),
                "detail_target": (
                    "ctl00$PageContent$VW_PUBLIC_ESTINSPTableControlRepeater$"
                    f"{match.group(1)}$ViolationDetails"
                ),
                "inspection_date": values[1],
                "facility_name": values[2],
                "address": values[3],
                "state_id": values[4],
                "establishment_type": values[5],
                "final_score": values[6],
                "grade": values[7],
                "inspector_id": values[8],
            }
        )
    return rows


def parse_violations(detail_page: str) -> tuple[str, list[dict[str, str]]]:
    comments_match = re.search(
        r'INSPECTION_COMMENTSLabel">General Comments</span></td><td class="dfv"[^>]*>(.*?)</td>',
        detail_page,
        re.S,
    )
    general_comments = clean_html(comments_match.group(1)) if comments_match else ""
    violation_rows: list[dict[str, str]] = []
    for row_html in re.findall(
        r'<tr id="ctl00_PageContent_INSPECTION_VIOLATIONTableControlRepeater_[^"]+_critvio">(.*?)</tr>',
        detail_page,
        re.S,
    ):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)
        if len(cells) < 7:
            continue
        values = [clean_html(cell) for cell in cells]
        violation_rows.append(
            {
                "item": values[0],
                "demerits": values[1],
                "description": values[2],
                "corrected_during_inspection": values[3],
                "repeat": values[4],
                "verification_required": values[5],
                "comments": values[6],
            }
        )
    return general_comments, violation_rows


def row_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (row["state_id"], row["inspection_date"], row["facility_name"].lower())


def archive_key(row: dict[str, object]) -> str:
    return "|".join(
        str(row.get(field, "")).strip().lower()
        for field in ("state_id", "inspection_date", "facility_name", "address")
    )


def load_existing_rows(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        return {}
    return {
        archive_key(row): row
        for row in rows
        if isinstance(row, dict) and archive_key(row)
    }


def main() -> None:
    captured_at = datetime.now().astimezone().isoformat(timespec="seconds")
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    base_page = fetch_page(opener)
    specs = [
        SearchSpec("grade_c_restaurants", "C", "100"),
        SearchSpec("grade_b_restaurants", "B", "100"),
        SearchSpec("recent_restaurants", "--ANY--", "100"),
    ]

    list_pages: list[tuple[str, str]] = []
    for spec in specs:
        list_pages.append((spec.label, search_page(opener, base_page, spec)))
        time.sleep(0.4)

    rows_by_key: dict[tuple[str, str, str], tuple[dict[str, str], str]] = {}
    for label, page in list_pages:
        for row in parse_list_rows(page, label):
            rows_by_key.setdefault(row_key(row), (row, page))

    output_rows: list[dict[str, object]] = []
    for index, (row, list_page) in enumerate(list(rows_by_key.values())[:MAX_DETAILS], start=1):
        fields = form_fields(list_page)
        fields["__EVENTTARGET"] = row["detail_target"]
        fields["__EVENTARGUMENT"] = ""
        try:
            detail_page = fetch_page(opener, fields)
        except Exception as exc:
            print(f"Skipped Mecklenburg detail page {index}: {exc}", flush=True)
            continue
        general_comments, violations = parse_violations(detail_page)
        violation_text = "\n\n".join(
            f"{violation['item']} - {violation['description']}: {violation['comments']}"
            for violation in violations
            if violation["comments"] or violation["description"]
        )
        output_rows.append(
            {
                **row,
                "first_seen": captured_at,
                "last_seen": captured_at,
                "general_comments": general_comments,
                "violations": violations,
                "violation_text": violation_text or general_comments,
                "result": f"Score {row['final_score']} / Grade {row['grade']}",
                "official_url": BASE_URL,
            }
        )
        if index % 25 == 0:
            print(f"Captured {index} Mecklenburg detail pages...", flush=True)
        time.sleep(0.2)

    archived_rows = load_existing_rows(OUTPUT_PATH)
    for row in output_rows:
        key = archive_key(row)
        previous = archived_rows.get(key)
        if previous:
            row["first_seen"] = previous.get("first_seen", row["first_seen"])
        archived_rows[key] = row

    merged_rows = sorted(
        archived_rows.values(),
        key=lambda row: (
            str(row.get("inspection_date", "")),
            str(row.get("last_seen", "")),
            str(row.get("facility_name", "")),
        ),
        reverse=True,
    )

    payload = {
        "capturedAt": captured_at,
        "source": "Mecklenburg County Public Health Inspections",
        "sourceUrl": BASE_URL,
        "lookbackDays": LOOKBACK_DAYS,
        "newOrUpdatedRows": len(output_rows),
        "rows": merged_rows,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(merged_rows)} archived rows to {OUTPUT_PATH} ({len(output_rows)} refreshed)")


if __name__ == "__main__":
    main()
