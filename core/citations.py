"""Grounding and citation audit helpers for local legal references.

The auditor treats source payloads as evidence, not answer text.  In
particular, citation identifiers contained in ``local_references`` or other
metadata fields cannot accidentally increase the answer's coverage score.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any


_CITATION_ID_RE = re.compile(r"\[\s*[Ll]([1-9]\d*)\s*\]")
_CITATION_ID_VALUE_RE = re.compile(r"^[Ll]([1-9]\d*)$")

_CN_NUMBER_CHARS = "零〇○一二三四五六七八九十百千万两壹贰叁肆伍陆柒捌玖拾佰仟萬0-9"
_NAMED_CITATION_RE = re.compile(
    rf"《\s*(?P<law_name>[^》\r\n]{{2,80}}?)\s*》\s*"
    rf"第\s*(?P<article>[{_CN_NUMBER_CHARS}]+)\s*条"
    rf"(?:\s*之\s*(?P<subarticle>[{_CN_NUMBER_CHARS}]+))?"
)

_CLAIM_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])|\r?\n+")
_ALIGNMENT_CANONICALISATIONS = (
    ("薪资", "劳动报酬"),
    ("薪酬", "劳动报酬"),
    ("工资", "劳动报酬"),
    ("企业", "用人单位"),
    ("公司", "用人单位"),
    ("雇主", "用人单位"),
    ("员工", "劳动者"),
    ("必须", "应当"),
    ("须", "应当"),
    ("发放", "支付"),
)
_ALIGNMENT_BOILERPLATE = (
    "依据",
    "根据",
    "结合",
    "可见",
    "因此",
    "所以",
    "规则见",
    "结论来自",
    "相关规定",
    "应当",
    "依法",
    "规定",
)

# These are transport/source/debug fields, rather than prose generated as the
# answer.  Keys are compared after case-folding and removing separators.
_DEFAULT_EXCLUDED_FIELDS = {
    "local_references",
    "references",
    "source_references",
    "retrieved_references",
    "retrieved_context",
    "knowledge_base",
    "sources",
    "source_documents",
    "source_materials",
    "citation_audit",
    "audit_metadata",
    "metadata",
    "_meta",
    "privacy_summary",
    "redaction_summary",
    "debug",
    "trace",
    "question",
    "query",
    "prompt",
    "input",
    "original_input",
}

_CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "○": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "壹": 1,
    "贰": 2,
    "叁": 3,
    "肆": 4,
    "伍": 5,
    "陆": 6,
    "柒": 7,
    "捌": 8,
    "玖": 9,
}
_SMALL_UNITS = {"十": 10, "拾": 10, "百": 100, "佰": 100, "千": 1000, "仟": 1000}
_LARGE_UNITS = {"万": 10000, "萬": 10000}


def _normalise_field_name(value: Any) -> str:
    return re.sub(r"[\s_\-]", "", str(value)).casefold()


def _normalise_citation_id(value: Any) -> str | None:
    match = _CITATION_ID_VALUE_RE.fullmatch(str(value).strip())
    return f"L{int(match.group(1))}" if match else None


def _unique_in_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def extract_auditable_text(
    value: Any,
    excluded_fields: Iterable[str] | None = None,
) -> str:
    """Flatten answer text while excluding source and transport metadata."""

    excluded_source = set(_DEFAULT_EXCLUDED_FIELDS)
    if excluded_fields is not None:
        excluded_source.update(excluded_fields)
    excluded = {_normalise_field_name(field) for field in excluded_source}
    fragments: list[str] = []

    def walk(item: Any) -> None:
        if isinstance(item, str):
            fragments.append(item)
            return
        if isinstance(item, Mapping):
            for key, child in item.items():
                if _normalise_field_name(key) in excluded:
                    continue
                walk(child)
            return
        if isinstance(item, (list, tuple, set)):
            for child in item:
                walk(child)

    walk(value)
    return "\n".join(fragments)


def extract_citation_ids(
    value: Any,
    excluded_fields: Iterable[str] | None = None,
) -> list[str]:
    """Extract unique ``[L<number>]`` identifiers in first-use order."""

    text = value if isinstance(value, str) else extract_auditable_text(value, excluded_fields)
    return _unique_in_order(f"L{int(match.group(1))}" for match in _CITATION_ID_RE.finditer(text))


def _chinese_number_to_int(value: str) -> int | None:
    compact = re.sub(r"\s+", "", value)
    if not compact:
        return None
    if compact.isdigit():
        return int(compact)

    # Forms such as 五〇九 contain no positional units and are read digit by
    # digit, while 五百零九 is evaluated with Chinese units.
    if not any(character in _SMALL_UNITS or character in _LARGE_UNITS for character in compact):
        if not all(character in _CHINESE_DIGITS for character in compact):
            return None
        return int("".join(str(_CHINESE_DIGITS[character]) for character in compact))

    total = 0
    section = 0
    number = 0
    for character in compact:
        if character.isdigit():
            number = number * 10 + int(character)
        elif character in _CHINESE_DIGITS:
            number = _CHINESE_DIGITS[character]
        elif character in _SMALL_UNITS:
            unit = _SMALL_UNITS[character]
            section += (number if number else 1) * unit
            number = 0
        elif character in _LARGE_UNITS:
            section += number
            total += (section if section else 1) * _LARGE_UNITS[character]
            section = 0
            number = 0
        else:
            return None
    return total + section + number


def _article_key(value: Any) -> tuple[int, int | None] | None:
    text = str(value or "").strip()
    if not text:
        return None
    pattern = re.compile(
        rf"(?:第\s*)?(?P<article>[{_CN_NUMBER_CHARS}]+)\s*(?:条)?"
        rf"(?:\s*之\s*(?P<subarticle>[{_CN_NUMBER_CHARS}]+))?"
    )
    match = pattern.search(text)
    if not match:
        return None
    article = _chinese_number_to_int(match.group("article"))
    subarticle = (
        _chinese_number_to_int(match.group("subarticle"))
        if match.group("subarticle") is not None
        else None
    )
    return (article, subarticle) if article is not None else None


def _normalise_law_name(value: Any) -> str:
    text = str(value or "").strip()
    text = text.removeprefix("《").removesuffix("》")
    return re.sub(r"[\s·•]", "", text).casefold()


def _law_name_aliases(value: Any) -> set[str]:
    normalised = _normalise_law_name(value)
    aliases = {normalised} if normalised else set()
    prefix = "中华人民共和国"
    if normalised.startswith(prefix) and len(normalised) > len(prefix):
        aliases.add(normalised[len(prefix) :])
    return aliases


def extract_named_legal_citations(value: Any) -> list[dict[str, Any]]:
    """Extract citations such as ``《民法典》第五百零九条``."""

    text = value if isinstance(value, str) else extract_auditable_text(value)
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[int, int | None]]] = set()
    for match in _NAMED_CITATION_RE.finditer(text):
        law_name = match.group("law_name").strip()
        article_text = match.group("article")
        subarticle_text = match.group("subarticle")
        article = f"第{article_text}条"
        if subarticle_text:
            article += f"之{subarticle_text}"
        key = (_normalise_law_name(law_name), _article_key(article))
        if key[1] is None or key in seen:
            continue
        seen.add(key)
        found.append(
            {
                "law_name": law_name,
                "article": article,
                "article_number": key[1][0],
                "subarticle_number": key[1][1],
                "display": f"《{law_name}》{article}",
            }
        )
    return found


def _coerce_sources(value: Any) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        nested = value.get("local_references")
        if isinstance(nested, (list, tuple)):
            value = nested
        else:
            value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    return [source for source in value if isinstance(source, Mapping)]


def _source_law_name(source: Mapping[str, Any]) -> Any:
    return source.get("law_name") or source.get("law") or source.get("title") or source.get("name")


def _source_article(source: Mapping[str, Any]) -> Any:
    return source.get("article") or source.get("article_no") or source.get("article_number")


def _named_citation_matches_source(
    citation: Mapping[str, Any],
    source: Mapping[str, Any],
) -> bool:
    citation_aliases = _law_name_aliases(citation.get("law_name"))
    source_aliases = _law_name_aliases(_source_law_name(source))
    if not citation_aliases or citation_aliases.isdisjoint(source_aliases):
        return False
    return _article_key(citation.get("article")) == _article_key(_source_article(source))


def _normalise_alignment_text(value: Any) -> str:
    """Return a conservative comparison form, without pretending to parse semantics."""

    text = _CITATION_ID_RE.sub("", str(value or "")).casefold()
    for old, new in _ALIGNMENT_CANONICALISATIONS:
        text = text.replace(old, new)
    for phrase in _ALIGNMENT_BOILERPLATE:
        text = text.replace(phrase, "")
    return "".join(re.findall(r"[\u3400-\u9fff]|[a-z0-9]", text))


def _character_ngrams(text: str, size: int) -> set[str]:
    if len(text) < size:
        return set()
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def _longest_common_span(left: str, right: str) -> str:
    """Find a longest contiguous character span using a small dynamic program."""

    if not left or not right:
        return ""
    previous = [0] * (len(right) + 1)
    best_length = 0
    best_end = 0
    for left_index, left_character in enumerate(left, 1):
        current = [0] * (len(right) + 1)
        for right_index, right_character in enumerate(right, 1):
            if left_character == right_character:
                current[right_index] = previous[right_index - 1] + 1
                if current[right_index] > best_length:
                    best_length = current[right_index]
                    best_end = left_index
        previous = current
    return left[best_end - best_length : best_end]


def _claim_segments(text: str) -> list[str]:
    """Split prose while attaching a marker-only sentence to its predecessor."""

    pieces = [piece.strip() for piece in _CLAIM_SPLIT_RE.split(text) if piece.strip()]
    segments: list[str] = []
    for index, piece in enumerate(pieces):
        if not _CITATION_ID_RE.search(piece):
            continue
        claim_without_ids = _normalise_alignment_text(piece)
        if len(claim_without_ids) < 4 and index:
            segments.append(f"{pieces[index - 1]}{piece}")
        else:
            segments.append(piece)
    return segments


def _source_content(source: Mapping[str, Any]) -> str:
    return str(
        source.get("content")
        or source.get("text")
        or source.get("full_text")
        or source.get("summary")
        or ""
    )


def _align_claim_to_source(
    citation_id: str,
    claim_segment: str,
    source: Mapping[str, Any],
) -> dict[str, Any]:
    """Estimate only lexical support; this is not semantic or legal validation."""

    claim = _normalise_alignment_text(claim_segment)
    content = _normalise_alignment_text(_source_content(source))
    law_name = _normalise_alignment_text(_source_law_name(source))
    article = _normalise_alignment_text(_source_article(source))

    bigrams_claim = _character_ngrams(claim, 2)
    bigrams_source = _character_ngrams(content, 2)
    trigrams_claim = _character_ngrams(claim, 3)
    trigrams_source = _character_ngrams(content, 3)
    shared_bigrams = bigrams_claim & bigrams_source
    shared_trigrams = trigrams_claim & trigrams_source

    def containment(shared: set[str], claim_ngrams: set[str]) -> float:
        return len(shared) / len(claim_ngrams) if claim_ngrams else 0.0

    bigram_overlap = containment(shared_bigrams, bigrams_claim)
    trigram_overlap = containment(shared_trigrams, trigrams_claim)
    overlap_score = round(0.55 * bigram_overlap + 0.45 * trigram_overlap, 4)
    longest_span = _longest_common_span(claim, content)
    law_name_match = bool(law_name and law_name in claim)
    article_match = bool(article and article in claim)
    identity_remainder = claim
    if law_name_match:
        identity_remainder = identity_remainder.replace(law_name, "")
    if article_match:
        identity_remainder = identity_remainder.replace(article, "")

    # A four-character shared content span is fairly strong for Chinese legal
    # text.  The n-gram branch admits ordinary paraphrases such as
    # "工资/劳动报酬" after the deliberately small synonym normalisation above.
    if law_name_match and article_match and len(identity_remainder) < 4:
        verdict = "pass"
        reason = "该句段仅标识了与来源一致的法律名称和条号"
    elif not content:
        verdict = "not_evaluated"
        reason = "来源缺少可比较的正文内容"
    elif len(longest_span) >= 4 or (
        overlap_score >= 0.16 and len(shared_bigrams) >= 2
    ):
        verdict = "pass"
        reason = "主张与来源正文存在可观察的字符片段重合"
    elif len(claim) < 6:
        verdict = "not_evaluated"
        reason = "引用所在主张过短，无法可靠进行词面对齐"
    elif not shared_bigrams and len(longest_span) < 2:
        verdict = "fail"
        reason = "引用所在主张与来源正文未发现实质性词面重合，疑似明显错引"
    else:
        verdict = "warning"
        reason = "仅发现较弱的词面重合，需人工核对该引用是否支持主张"

    return {
        "citation_id": citation_id,
        "claim": _CITATION_ID_RE.sub("", claim_segment).strip(),
        "verdict": verdict,
        "overlap_score": overlap_score,
        "bigram_overlap": round(bigram_overlap, 4),
        "trigram_overlap": round(trigram_overlap, 4),
        "longest_common_span": longest_span,
        "shared_fragments": sorted(shared_trigrams, key=lambda item: (-len(item), item))[:5],
        "law_name_match": law_name_match,
        "article_match": article_match,
        "reason": reason,
    }


def _audit_claim_alignment(
    auditable_text: str,
    source_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for segment in _claim_segments(auditable_text):
        for citation_id in extract_citation_ids(segment):
            source = source_by_id.get(citation_id)
            if source is not None:
                items.append(_align_claim_to_source(citation_id, segment, source))

    failed_ids = _unique_in_order(
        item["citation_id"] for item in items if item["verdict"] == "fail"
    )
    warning_ids = _unique_in_order(
        item["citation_id"] for item in items if item["verdict"] == "warning"
    )
    not_evaluated_ids = _unique_in_order(
        item["citation_id"] for item in items if item["verdict"] == "not_evaluated"
    )
    return {
        "method": "确定性中文字符二/三元组重合 + 最长公共片段 + 少量同义词归一化",
        "scope": "仅检查引用所在句段与来源 law_name/article/content 的词面对齐",
        "disclaimer": "该结果不能证明语义正确、法律适用正确或来源具有法律效力",
        "items": items,
        "failed_ids": failed_ids,
        "warning_ids": warning_ids,
        "not_evaluated_ids": not_evaluated_ids,
    }


def audit_citations(
    result: Any,
    allowed_sources: Any = None,
    *,
    excluded_fields: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Audit local-source citations in a model result.

    Coverage is intentionally identifier-based: a named law/article citation
    is validated against allowed sources, but it does not silently substitute
    for the required ``[L1]`` traceability marker.
    """

    if allowed_sources is None and isinstance(result, Mapping):
        allowed_sources = result.get("local_references")
    sources = _coerce_sources(allowed_sources)

    source_by_id: dict[str, Mapping[str, Any]] = {}
    for index, source in enumerate(sources, 1):
        citation_id = _normalise_citation_id(source.get("citation_id")) or f"L{index}"
        source_by_id.setdefault(citation_id, source)

    auditable_text = extract_auditable_text(result, excluded_fields)
    cited_ids = extract_citation_ids(auditable_text)
    known_cited_ids = [citation_id for citation_id in cited_ids if citation_id in source_by_id]
    unknown_ids = [citation_id for citation_id in cited_ids if citation_id not in source_by_id]
    uncited_ids = [citation_id for citation_id in source_by_id if citation_id not in known_cited_ids]

    named_citations = extract_named_legal_citations(auditable_text)
    matched_named_citations: list[dict[str, Any]] = []
    unsupported_named_citations: list[str] = []
    for named_citation in named_citations:
        matched_ids = [
            citation_id
            for citation_id, source in source_by_id.items()
            if _named_citation_matches_source(named_citation, source)
        ]
        if matched_ids:
            matched_named_citations.append(
                {
                    "citation": named_citation["display"],
                    "source_ids": matched_ids,
                }
            )
        else:
            unsupported_named_citations.append(named_citation["display"])

    alignment = _audit_claim_alignment(auditable_text, source_by_id)

    source_count = len(source_by_id)
    coverage_percent = round(100.0 * len(known_cited_ids) / source_count, 2) if source_count else 0.0

    if unknown_ids or unsupported_named_citations or alignment["failed_ids"]:
        status = "fail"
        reasons: list[str] = []
        if unknown_ids:
            reasons.append(f"存在未知引用编号：{', '.join(unknown_ids)}")
        if unsupported_named_citations:
            reasons.append("存在未获允许来源支持的法律名称/条号引用")
        if alignment["failed_ids"]:
            reasons.append(
                "存在与来源正文明显缺乏词面对齐的引用："
                + ", ".join(alignment["failed_ids"])
            )
        message = "；".join(reasons)
    elif uncited_ids or alignment["warning_ids"] or alignment["not_evaluated_ids"]:
        status = "warning"
        reasons = []
        if uncited_ids:
            reasons.append(f"仍有 {len(uncited_ids)} 个本地来源未在回答正文中以 [L编号] 引用")
        if alignment["warning_ids"]:
            reasons.append(
                "部分引用仅有较弱词面对齐：" + ", ".join(alignment["warning_ids"])
            )
        if alignment["not_evaluated_ids"]:
            reasons.append(
                "部分引用无法完成词面对齐：" + ", ".join(alignment["not_evaluated_ids"])
            )
        message = "；".join(reasons)
    elif source_count:
        status = "pass"
        message = (
            "引用编号有效、来源覆盖完整且未发现明显词面错引；"
            "该结果不代表语义、法律适用或来源效力已获验证"
        )
    else:
        status = "insufficient"
        if auditable_text.strip():
            message = "没有可审计的本地来源，无法验证回答中的法律结论"
        else:
            message = "回答正文为空且没有本地来源，无法执行引用核验"

    return {
        "source_count": source_count,
        "cited_ids": cited_ids,
        "known_cited_ids": known_cited_ids,
        "unknown_ids": unknown_ids,
        "uncited_ids": uncited_ids,
        "coverage_percent": coverage_percent,
        "named_citations": named_citations,
        "matched_named_citations": matched_named_citations,
        "unsupported_named_citations": unsupported_named_citations,
        "alignment": alignment,
        "has_auditable_text": bool(auditable_text.strip()),
        "status": status,
        "message": message,
    }


__all__ = [
    "audit_citations",
    "extract_auditable_text",
    "extract_citation_ids",
    "extract_named_legal_citations",
]
