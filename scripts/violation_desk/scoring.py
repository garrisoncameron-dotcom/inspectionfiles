"""Gross Index scoring for inspection violations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

UTC = timezone.utc


@dataclass(frozen=True)
class Trigger:
    label: str
    pattern: re.Pattern[str]
    grossness: int
    severity: int
    violation_type: str
    desk_section: str


TRIGGERS = [
    Trigger(
        "roaches",
        re.compile(r"\b(cockroach|cockroaches|roach|roaches)\b", re.I),
        30,
        18,
        "Roaches / cockroaches",
        "The Vermin Wire",
    ),
    Trigger(
        "rodents",
        re.compile(r"\b(rat|rats|mouse|mice|rodent|rodents|vermin)\b", re.I),
        30,
        18,
        "Rodents / vermin",
        "The Vermin Wire",
    ),
    Trigger(
        "droppings",
        re.compile(r"\b(dropping|droppings|feces|excreta)\b", re.I),
        24,
        16,
        "Droppings / pest evidence",
        "The Vermin Wire",
    ),
    Trigger(
        "flies",
        re.compile(r"\b(flies|fly|gnat|gnats|maggot|maggots|insect|insects)\b", re.I),
        20,
        12,
        "Flies / insects",
        "The Vermin Wire",
    ),
    Trigger(
        "mold",
        re.compile(r"\b(mold|mould|slime|mildew)\b", re.I),
        22,
        13,
        "Mold / slime",
        "The Gross Index",
    ),
    Trigger(
        "sewage",
        re.compile(r"\b(sewage|wastewater|waste water|sewer|flooding|unable to flush)\b", re.I),
        30,
        20,
        "Sewage / wastewater",
        "The Closure Watch",
    ),
    Trigger(
        "unsafe temperature",
        re.compile(r"\b(temperature|cold holding|hot holding|41f|135f|danger zone)\b", re.I),
        10,
        15,
        "Unsafe temperature",
        "The Gross Index",
    ),
    Trigger(
        "cross contamination",
        re.compile(r"\b(cross[- ]contamination|contaminated|adulterated)\b", re.I),
        12,
        15,
        "Contamination",
        "The Gross Index",
    ),
    Trigger(
        "no water",
        re.compile(r"\b(no hot water|no water|handwash|handwashing)\b", re.I),
        10,
        15,
        "Water / handwashing failure",
        "The Gross Index",
    ),
    Trigger(
        "closure",
        re.compile(r"\b(closed|ordered closed|permit suspended|suspended|imminent health)\b", re.I),
        20,
        20,
        "Closure / permit issue",
        "The Closure Watch",
    ),
]


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = None
        for date_format in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                parsed = datetime.strptime(value[:10], date_format)
                break
            except ValueError:
                continue
        if parsed is None:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def recency_points(inspection_date: datetime | None, now: datetime | None = None) -> int:
    if not inspection_date:
        return 0

    now = now or datetime.now(UTC)
    days = max((now - inspection_date).days, 0)
    if days <= 30:
        return 10
    if days <= 90:
        return 7
    if days <= 365:
        return 4
    return 1


def score_text(
    text: str,
    result_text: str = "",
    inspection_date: datetime | None = None,
    repeat_points: int = 0,
) -> dict[str, object]:
    haystack = f"{text or ''} {result_text or ''}".strip()
    matches = [trigger for trigger in TRIGGERS if trigger.pattern.search(haystack)]

    grossness = max((trigger.grossness for trigger in matches), default=0)
    severity = max((trigger.severity for trigger in matches), default=0)
    recency = recency_points(inspection_date)
    verifiability = 10
    story_value = 8 if matches else 0

    if re.search(r"\b(famous|stadium|airport|hotel|casino|celebrity|historic)\b", haystack, re.I):
        story_value = max(story_value, 15)

    closure_match = re.search(r"\b(fail|failed|closed|suspended|out of business|pass w/ conditions)\b", result_text, re.I)
    if closure_match:
        severity = max(severity, 15)
        story_value = max(story_value, 10)

    if re.search(r"\bnot critical\b", result_text, re.I):
        severity = min(severity, 8)

    observed_pest_activity = re.search(
        r"\b(live|dead|crawling|dropping|droppings|feces|excreta|infestation|observed over|observed about|approximately \d+|pest activity|vermin activity|rodent activity|insect activity|flies|maggot|maggots)\b",
        haystack,
        re.I,
    )
    preventive_pest_language = re.search(
        r"\b(rodent proof\w*|pest control logbook|outer opening|door gap|not tight fitting|protect(ed)? outer openings|weather strip|sweep|keep doors? closed|door propp?ed|propp?ed open|door left open)\b",
        haystack,
        re.I,
    )
    if preventive_pest_language and not observed_pest_activity:
        grossness = min(grossness, 8)
        severity = min(severity, 8)

    if re.search(r"\banti-siphonage|back-flow|backflow\b", haystack, re.I) and not re.search(
        r"\bblack|dirty water|backup|backing up|flooding|unable to flush|overflow|sewage associated|flies|maggot|roach|rodent|dropping\b",
        haystack,
        re.I,
    ):
        grossness = min(grossness, 10)
        severity = min(severity, 8)

    score = min(
        100,
        grossness + severity + story_value + recency + min(repeat_points, 10) + verifiability,
    )

    primary = max(matches, key=lambda trigger: trigger.grossness + trigger.severity, default=None)

    return {
        "score": score,
        "grossness": grossness,
        "severity": severity,
        "story_value": story_value,
        "recency": recency,
        "repeat_pattern": min(repeat_points, 10),
        "verifiability": verifiability,
        "matched_terms": [trigger.label for trigger in matches],
        "violation_type": primary.violation_type if primary else "Other",
        "desk_section": primary.desk_section if primary else "The Gross Index",
    }


def extract_grossest_detail(text: str, limit: int = 320) -> str:
    if not text:
        return ""

    sentences = re.split(r"\s+\|\s+|(?<=[.!?])\s+|\n+", text.strip())
    ranked = sorted(
        sentences,
        key=lambda sentence: score_text(sentence)["score"],
        reverse=True,
    )
    detail = ranked[0].strip() if ranked else text.strip()
    if len(detail) <= limit:
        return detail
    return detail[: limit - 3].rstrip() + "..."
