"""Check provenance and minimum quality of the student-oriented case snapshot."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "legal_cases_student_200.json"
REQUIRED = (
    "slug", "title", "summary", "dispute_focus", "judgment_result",
    "judgment_reasoning", "ai_plain_language", "source_external_id",
    "source_publisher", "source_url", "published_at", "legal_domain",
)


def validate() -> dict:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    errors: list[str] = []
    if payload.get("schema_version") != 1 or payload.get("case_count") != 200 or len(cases) != 200:
        errors.append("expected schema 1 and exactly 200 cases")

    for index, case in enumerate(cases, 1):
        label = case.get("slug") or f"row-{index}"
        for field in REQUIRED:
            if not str(case.get(field) or "").strip():
                errors.append(f"{label}: missing {field}")
        if not case.get("slug", "").startswith("spc-student-"):
            errors.append(f"{label}: unexpected slug")
        url = urlparse(case.get("source_url", ""))
        if url.scheme != "https" or url.hostname != "www.court.gov.cn":
            errors.append(f"{label}: source must be a highest-court HTTPS page")
        if case.get("source_publisher") != "中华人民共和国最高人民法院":
            errors.append(f"{label}: source publisher must be in Chinese")
        if case.get("source_type") != "official_court_typical":
            errors.append(f"{label}: unexpected internal source type")
        try:
            published = date.fromisoformat(case.get("published_at", ""))
            if published.year < 2023 or published > date(2026, 9, 28):
                errors.append(f"{label}: release date outside requested period")
        except ValueError:
            errors.append(f"{label}: invalid release date")
        if len(case.get("summary", "")) < 40 or case.get("summary", "").endswith("…"):
            errors.append(f"{label}: incomplete summary")
        for field in ("judgment_result", "judgment_reasoning"):
            text = case.get(field, "")
            if len(text) < 15 or text.endswith("…"):
                errors.append(f"{label}: incomplete {field}")
        if not case.get("categories") or not case.get("tags"):
            errors.append(f"{label}: missing categorization")
        laws = case.get("laws") or []
        if not laws:
            errors.append(f"{label}: missing law")
        for law in laws:
            article = law.get("article", "")
            note = law.get("note", "")
            if not law.get("law_name") or not re.search(r"第[^，；。]{1,40}条", article):
                errors.append(f"{label}: law must name a specific article")
            if "条文要点：" not in note or "对应事实：" not in note or "…" in note or len(note) > 500:
                errors.append(f"{label}: law explanation must be case-specific and fit storage")
            if article not in case.get("dispute_focus", ""):
                errors.append(f"{label}: issue question must identify the linked article")
        if case.get("image_url") and not case.get("image_source_url"):
            errors.append(f"{label}: image lacks official provenance")

    for field in ("slug", "source_external_id"):
        duplicates = [value for value, count in Counter(case.get(field) for case in cases).items() if count > 1]
        if duplicates:
            errors.append(f"duplicate {field}: {duplicates[:3]}")

    domains = Counter(case.get("legal_domain") for case in cases)
    pages = len({case.get("source_url") for case in cases})
    if len(domains) < 8 or pages < 30:
        errors.append(f"coverage too narrow: {len(domains)} domains, {pages} official pages")
    if errors:
        raise SystemExit("student case validation failed:\n- " + "\n- ".join(errors[:40]))
    return {
        "cases": len(cases),
        "official_pages": pages,
        "legal_domains": dict(sorted(domains.items())),
        "release_years": dict(sorted(Counter(case["published_at"][:4] for case in cases).items())),
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
