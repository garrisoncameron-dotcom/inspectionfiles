"""Public inspection data sources for the Violation Desk MVP."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    endpoint: str
    agency: str
    date_field: str
    text_field: str
    name_field: str
    address_fields: tuple[str, ...]
    result_field: str | None = None
    query: str | None = None
    kind: str = "socrata"
    status: str = "live"
    notes: str = ""
    jurisdiction_path: str | None = None
    request_type: str | None = None


SOURCES: dict[str, Source] = {
    "nyc": Source(
        id="nyc",
        name="New York City Restaurant Inspection Results",
        endpoint="https://data.cityofnewyork.us/resource/43nn-pn8j.json",
        agency="NYC Department of Health and Mental Hygiene",
        date_field="inspection_date",
        text_field="violation_description",
        name_field="dba",
        address_fields=("building", "street", "boro", "zipcode"),
        result_field="critical_flag",
        query=(
            "violation_description IS NOT NULL "
            "AND inspection_date > '2025-01-01T00:00:00'"
        ),
    ),
    "chicago": Source(
        id="chicago",
        name="Chicago Food Inspections",
        endpoint="https://data.cityofchicago.org/resource/4ijn-s7e5.json",
        agency="Chicago Department of Public Health",
        date_field="inspection_date",
        text_field="violations",
        name_field="dba_name",
        address_fields=("address", "city", "state", "zip"),
        result_field="results",
        query="inspection_date > '2025-01-01T00:00:00'",
    ),
    "orange_county_closures": Source(
        id="orange_county_closures",
        name="Orange County Restaurant Closures",
        endpoint="data-snapshots/orange-county-closures.json",
        agency="OC Health Care Agency - Environmental Health Division",
        date_field="Closed On",
        text_field="Reason for Closure",
        name_field="Establishment Name",
        address_fields=("Address", "City", "Zip"),
        result_field="Result",
        kind="myhd_snapshot",
        jurisdiction_path="orange-county",
        request_type="inspclosures",
        notes=(
            "Pulled from the My Health Department restaurant-closures page. "
            "The hidden /genericEndpoint POST works in-browser but returns 403 to direct command-line fetches, "
            "so this source currently uses a browser-captured JSON snapshot."
        ),
    ),
    "myhd_inspection_snapshots": Source(
        id="myhd_inspection_snapshots",
        name="My Health Department Inspection Snapshots",
        endpoint="data-snapshots/myhd-inspection-snapshots.json",
        agency="Multiple My Health Department jurisdictions",
        date_field="inspectionDate",
        text_field="ReasonforClosure",
        name_field="FacilityName",
        address_fields=("addressLine1", "city", "zip"),
        result_field="result",
        kind="myhd_snapshot",
        status="snapshot_ready",
        notes=(
            "Reusable snapshot intake for inspections.myhealthdepartment.com jurisdictions. "
            "Rows are browser-captured because the vendor platform often returns 403 to direct command-line fetches."
        ),
    ),
    "la_county_closures": Source(
        id="la_county_closures",
        name="Los Angeles County Food Facility Closures",
        endpoint="data-snapshots/la-county-closures.json",
        agency="Los Angeles County Department of Public Health",
        date_field="Closed",
        text_field="Reason",
        name_field="Name",
        address_fields=("Address", "City"),
        result_field="Result",
        kind="local_json",
        notes=(
            "Browser-captured from the official Environmental Health Facility Closure List. "
            "This is a current closure/reopen feed with reasons such as vermin infestation, sewage discharge, "
            "and no method to clean and sanitize."
        ),
    ),
    "mecklenburg_county": Source(
        id="mecklenburg_county",
        name="Mecklenburg County Restaurant Inspections",
        endpoint="data-snapshots/mecklenburg-county-inspections.json",
        agency="Mecklenburg County Health Department",
        date_field="inspection_date",
        text_field="violation_text",
        name_field="facility_name",
        address_fields=("address",),
        result_field="result",
        kind="local_json",
        notes=(
            "Detailed restaurant inspection snapshot captured from the NC public environmental health portal. "
            "The fetcher follows each inspection's Violation Details postback so inspector comments are preserved."
        ),
    ),
    "los_angeles_county": Source(
        id="los_angeles_county",
        name="Los Angeles County Food Facility Inspections",
        endpoint="https://ehservices.publichealth.lacounty.gov/",
        agency="Los Angeles County Department of Public Health",
        date_field="inspection_date",
        text_field="violation_text",
        name_field="facility_name",
        address_fields=("address", "city", "zip"),
        kind="portal",
        status="adapter_needed",
        notes="High-priority portal source. Needs browser/form adapter and closure/reopen mapping.",
    ),
    "san_francisco": Source(
        id="san_francisco",
        name="San Francisco Health Inspection Scores",
        endpoint="https://data.sfgov.org/resource/pyih-qa8i.json",
        agency="San Francisco Department of Public Health",
        date_field="inspection_date",
        text_field="violation_description",
        name_field="business_name",
        address_fields=("business_address", "business_city", "business_state", "business_postal_code"),
        result_field="risk_category",
        query="violation_description IS NOT NULL",
        notes=(
            "Live Socrata source with violation_description and risk_category fields. "
            "This dataset is historical, so it is useful for archive/repeat-pattern research but not current closure monitoring."
        ),
    ),
    "santa_clara_county": Source(
        id="santa_clara_county",
        name="Santa Clara County Food Facility Inspections",
        endpoint="https://services.sccgov.org/facilityinspection/",
        agency="Santa Clara County Department of Environmental Health",
        date_field="inspection_date",
        text_field="violation_text",
        name_field="facility_name",
        address_fields=("address", "city", "zip"),
        kind="portal",
        status="adapter_needed",
        notes="Important Bay Area source for closures and vermin stories. Needs portal adapter.",
    ),
    "clark_county": Source(
        id="clark_county",
        name="Clark County / Las Vegas Food Establishment Inspections",
        endpoint="https://www.southernnevadahealthdistrict.org/permits-and-regulations/restaurant-inspections/",
        agency="Southern Nevada Health District",
        date_field="inspection_date",
        text_field="violation_text",
        name_field="facility_name",
        address_fields=("address", "city", "zip"),
        kind="portal",
        status="adapter_needed",
        notes="Las Vegas source. Needs inspection-search adapter and violation mapping.",
    ),
    "miami_dade": Source(
        id="miami_dade",
        name="Miami-Dade Food Service Inspections",
        endpoint="https://www.myfloridalicense.com/inspectionDates.asp",
        agency="Florida DBPR / Miami-Dade local food inspection records",
        date_field="inspection_date",
        text_field="violation_text",
        name_field="facility_name",
        address_fields=("address", "city", "zip"),
        kind="state_portal",
        status="adapter_needed",
        notes="Florida records are state-run. Needs search/detail adapter and county filtering.",
    ),
    "dc": Source(
        id="dc",
        name="Washington DC Food Establishment Inspections",
        endpoint="https://dc.healthinspections.us/",
        agency="DC Health",
        date_field="inspection_date",
        text_field="violation_text",
        name_field="facility_name",
        address_fields=("address", "city", "zip"),
        kind="dc_portal",
        status="live",
        notes=(
            "Live form-post portal adapter. Searches recent inspections, follows HTML report links, "
            "and scores stripped inspection report text."
        ),
    ),
    "king_county": Source(
        id="king_county",
        name="King County / Seattle Food Establishment Inspections",
        endpoint="https://kingcounty.gov/en/dept/dph/health-safety/food-safety/inspection-system",
        agency="Public Health - Seattle & King County",
        date_field="inspection_date",
        text_field="violation_text",
        name_field="facility_name",
        address_fields=("address", "city", "zip"),
        kind="portal",
        status="adapter_needed",
        notes="Needs portal adapter or export endpoint mapping.",
    ),
    "maricopa_county": Source(
        id="maricopa_county",
        name="Maricopa County Environmental Services Inspections",
        endpoint="https://envapp.maricopa.gov/EnvironmentalHealth/FoodInspection",
        agency="Maricopa County Environmental Services Department",
        date_field="inspection_date",
        text_field="violation_text",
        name_field="facility_name",
        address_fields=("address", "city", "zip"),
        kind="portal",
        status="adapter_needed",
        notes="Phoenix-area source. Needs portal adapter and violation text mapping.",
    ),
    "stadium_airport_watch": Source(
        id="stadium_airport_watch",
        name="Major Stadium and Airport Concession Systems",
        endpoint="source-list",
        agency="Multiple local health agencies",
        date_field="inspection_date",
        text_field="violation_text",
        name_field="facility_name",
        address_fields=("venue", "address", "city", "state"),
        kind="composite",
        status="source_discovery",
        notes="Composite desk section. Requires venue list matched against local inspection jurisdictions.",
    ),
}
