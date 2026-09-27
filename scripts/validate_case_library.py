"""Fail fast when the bundled legal case snapshot loses quality or provenance."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "legal_cases_200.json"
REQUIRED_TEXT = (
    "slug", "title", "summary", "dispute_focus", "judgment_result",
    "judgment_reasoning", "ai_plain_language", "source_external_id", "source_url",
)


def validate() -> dict:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    errors: list[str] = []
    if payload.get("case_count") != 193 or len(cases) != 193:
        errors.append(f"expected 193 supplemental cases, got {len(cases)}")
    if payload.get("total_with_core_cases") != 200:
        errors.append("total_with_core_cases must be 200")

    for index, case in enumerate(cases, 1):
        label = case.get("source_external_id") or f"row-{index}"
        for field in REQUIRED_TEXT:
            if not str(case.get(field) or "").strip():
                errors.append(f"{label}: missing {field}")
        source = urlparse(case.get("source_url", ""))
        if source.scheme != "https" or source.hostname not in {"court.gov.cn", "www.court.gov.cn"}:
            errors.append(f"{label}: source is not an official court.gov.cn HTTPS URL")
        if case.get("source_type") != "official_court_guiding":
            errors.append(f"{label}: unexpected source_type")
        if not case.get("laws"):
            errors.append(f"{label}: missing related law")
        if not case.get("categories"):
            errors.append(f"{label}: missing category")
        if case.get("image_url"):
            image = urlparse(case["image_url"])
            image_source = urlparse(case.get("image_source_url", ""))
            if image.scheme != "https" or not image.hostname:
                errors.append(f"{label}: image URL must use HTTPS")
            if image_source.scheme != "https" or not image_source.hostname:
                errors.append(f"{label}: image is missing an HTTPS provenance URL")

    for key in ("slug", "source_external_id", "source_url"):
        values = [case.get(key) for case in cases]
        duplicates = [value for value, count in Counter(values).items() if count > 1]
        if duplicates:
            errors.append(f"duplicate {key}: {duplicates[:3]}")

    category_counts = Counter(case["categories"][0] for case in cases if case.get("categories"))
    court_count = len({case["court_name"] for case in cases if case.get("court_name")})
    tag_counts = Counter(tag for case in cases for tag in case.get("tags", []))
    if len(category_counts) < 12:
        errors.append(f"expected at least 12 legal categories, got {len(category_counts)}")
    if court_count < 100:
        errors.append(f"expected at least 100 distinct court labels, got {court_count}")
    for tag, minimum in (("大学生高频", 35), ("社会热点", 100), ("日常生活", 45)):
        if tag_counts[tag] < minimum:
            errors.append(f"expected at least {minimum} cases tagged {tag}, got {tag_counts[tag]}")

    if errors:
        raise SystemExit("case library validation failed:\n- " + "\n- ".join(errors[:30]))
    return {
        "supplemental_cases": len(cases),
        "total_cases": payload["total_with_core_cases"],
        "categories": dict(sorted(category_counts.items())),
        "distinct_courts": court_count,
        "topic_tags": {key: tag_counts[key] for key in ("大学生高频", "社会热点", "日常生活")},
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
