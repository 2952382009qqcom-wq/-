"""Normalize model-produced module results before persistence or rendering.

External models occasionally follow the requested meaning while changing the
JSON shape, for example returning ``parties`` as objects instead of strings.
The UI must never expose Python/JavaScript object representations to users, so
this module converts known result schemas to stable, display-safe structures.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable


_EMPTY_MARKERS = {
    "",
    "-",
    "[object object]",
    "object object",
    "undefined",
    "null",
    "none",
    "nan",
}

_FIELD_LABELS = {
    "law_name": "法规",
    "article": "条款",
    "content": "内容",
    "note": "说明",
    "summary": "摘要",
    "suggestion": "建议",
    "title": "名称",
    "role": "身份",
    "party_role": "身份",
    "name": "姓名或名称",
    "party_name": "姓名或名称",
    "identity": "身份信息",
    "description": "说明",
    "value": "内容",
    "plaintiff": "原告",
    "defendant": "被告",
    "applicant": "申请人",
    "respondent": "被申请人",
    "appellant": "上诉人",
    "appellee": "被上诉人",
}

_PARTY_ROLE_KEYS = ("role", "party_role", "type", "角色", "诉讼地位", "当事人身份")
_PARTY_NAME_KEYS = ("name", "party_name", "party", "entity", "姓名", "名称", "当事人")
_PARTY_DETAIL_KEYS = ("identity", "description", "basic_info", "status", "身份信息", "基本信息")


def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)):
        return str(value)
    if not isinstance(value, str):
        return ""
    text = " ".join(value.replace("\x00", " ").split()).strip()
    return "" if text.casefold() in _EMPTY_MARKERS else text


def _first_text(mapping: dict, keys: Iterable[str]) -> str:
    for key in keys:
        text = display_text(mapping.get(key))
        if text:
            return text
    return ""


def display_text(value: Any, *, depth: int = 0) -> str:
    """Return readable text for a model value, never a language object token."""
    if depth > 4:
        return ""
    scalar = _clean_string(value)
    if scalar:
        return scalar
    if isinstance(value, (list, tuple, set)):
        items = [display_text(item, depth=depth + 1) for item in value]
        return "；".join(item for item in items if item)
    if isinstance(value, dict):
        law_name = _clean_string(value.get("law_name"))
        if law_name:
            article = display_text(value.get("article"), depth=depth + 1)
            detail = (
                display_text(value.get("content"), depth=depth + 1)
                or display_text(value.get("note"), depth=depth + 1)
                or display_text(value.get("applicability"), depth=depth + 1)
            )
            heading = f"《{law_name.strip('《》')}》{article}"
            return f"{heading}：{detail}" if detail else heading

        parts: list[str] = []
        for key, nested in value.items():
            text = display_text(nested, depth=depth + 1)
            if not text:
                continue
            label = _FIELD_LABELS.get(str(key), str(key) if any("\u3400" <= char <= "\u9fff" for char in str(key)) else "")
            parts.append(f"{label}：{text}" if label else text)
        return "；".join(parts)
    return ""


def _looks_like_single_party(value: dict) -> bool:
    keys = set(value)
    return bool(keys.intersection(_PARTY_ROLE_KEYS + _PARTY_NAME_KEYS + _PARTY_DETAIL_KEYS))


def _party_text(value: Any, role_override: str = "") -> str:
    if isinstance(value, dict):
        role = role_override or _first_text(value, _PARTY_ROLE_KEYS)
        name = _first_text(value, _PARTY_NAME_KEYS)
        detail = _first_text(value, _PARTY_DETAIL_KEYS)
        if name:
            main = f"{role}：{name}" if role else name
            return f"{main}（{detail}）" if detail and detail not in {role, name} else main
        generic = display_text(value)
        if role and generic and generic != role:
            return f"{role}：{generic}"
        return role or generic
    text = display_text(value)
    if role_override and text:
        return f"{role_override}：{text}"
    return text


def normalize_parties(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict) and not _looks_like_single_party(value):
        candidates = [
            _party_text(info, _FIELD_LABELS.get(str(role), str(role)))
            for role, info in value.items()
        ]
    else:
        source = value if isinstance(value, (list, tuple, set)) else [value]
        candidates = [_party_text(item) for item in source]
    result: list[str] = []
    for item in candidates:
        text = _clean_string(item)
        if text and text not in result:
            result.append(text)
    return result


def normalize_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    source = value if isinstance(value, (list, tuple, set)) else [value]
    result: list[str] = []
    for item in source:
        text = display_text(item)
        if text and text not in result:
            result.append(text)
    return result


def _normalize_object_list(value: Any, fields: tuple[str, ...], primary: str, numeric: tuple[str, ...] = ()) -> list[dict]:
    if value is None:
        return []
    source = value if isinstance(value, (list, tuple)) else [value]
    result: list[dict] = []
    for item in source:
        if isinstance(item, dict):
            normalized: dict[str, Any] = {}
            for field in fields:
                raw = item.get(field)
                if field in numeric:
                    try:
                        normalized[field] = float(raw) if raw not in (None, "") else 0
                    except (TypeError, ValueError):
                        normalized[field] = 0
                else:
                    normalized[field] = display_text(raw)
        else:
            normalized = {field: "" for field in fields}
            normalized[primary] = display_text(item)
        if any(value not in ("", 0, None) for value in normalized.values()):
            result.append(normalized)
    return result


def _normalize_string_fields(result: dict, fields: tuple[str, ...]) -> None:
    for field in fields:
        result[field] = display_text(result.get(field))


def _normalize_string_lists(result: dict, fields: tuple[str, ...]) -> None:
    for field in fields:
        result[field] = normalize_text_list(result.get(field))


def normalize_module_result(value: Any, stage: str) -> dict:
    """Normalize the known public result schema for a professional tool."""
    if not isinstance(value, dict):
        return {}
    result = deepcopy(value)

    if stage == "analyze":
        _normalize_string_fields(result, ("document_type", "overall_assessment"))
        result["parties"] = normalize_parties(result.get("parties"))
        _normalize_string_lists(result, ("legal_basis", "revision_suggestions"))
        result["key_clauses"] = _normalize_object_list(
            result.get("key_clauses"),
            ("clause", "summary", "risk_level", "note"),
            "summary",
        )
        result["risk_points"] = _normalize_object_list(
            result.get("risk_points"),
            ("point", "level", "suggestion"),
            "point",
        )
    elif stage == "search":
        _normalize_string_fields(result, ("question", "legal_analysis", "practical_advice"))
        _normalize_string_lists(result, ("related_cases",))
        result["provisions"] = _normalize_object_list(
            result.get("provisions"),
            ("law_name", "article", "content", "effective_date", "applicability"),
            "content",
        )
    elif stage == "review":
        _normalize_string_fields(result, ("contract_type", "overall_risk_level", "summary"))
        _normalize_string_lists(result, ("missing_clauses",))
        result["risk_items"] = _normalize_object_list(
            result.get("risk_items"),
            ("clause_text", "risk_type", "risk_level", "risk_score", "explanation", "revised_text", "legal_basis"),
            "explanation",
            ("risk_score",),
        )
    elif stage == "generate":
        _normalize_string_fields(result, ("title", "body", "document_type"))
        _normalize_string_lists(result, ("attachments", "notes"))
    elif stage == "strategy":
        _normalize_string_fields(
            result,
            ("case_type", "cause_of_action", "jurisdiction_analysis", "statute_of_limitation", "success_probability"),
        )
        _normalize_string_lists(result, ("applicable_laws", "key_evidence", "evidence_risks", "similar_cases", "next_steps"))
        strategy = result.get("legal_strategy")
        if isinstance(strategy, dict):
            result["legal_strategy"] = {
                key: display_text(strategy.get(key))
                for key in ("primary", "alternative", "settlement_advice")
            }
        elif display_text(strategy):
            result["legal_strategy"] = {"primary": display_text(strategy), "alternative": "", "settlement_advice": ""}
        else:
            result["legal_strategy"] = {}
    elif stage == "student_legal":
        _normalize_string_fields(
            result,
            ("issue_type", "legal_relationship", "school_rule_boundary", "communication_template", "disclaimer"),
        )
        _normalize_string_lists(
            result,
            ("applicable_laws", "rights_and_obligations", "evidence_checklist", "action_plan", "authority_channels"),
        )
        result["risk_points"] = _normalize_object_list(
            result.get("risk_points"),
            ("point", "level", "suggestion"),
            "point",
        )

    return result
