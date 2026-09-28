"""High-precision, recency-aware matching between user context and cases."""

import re
from datetime import date

from .models import LegalCase


STOP_TOKENS = {
    "一个", "这个", "那个", "怎么", "什么", "可以", "需要", "应该", "是否",
    "问题", "事情", "对方", "已经", "没有", "因为", "相关", "纠纷", "案件",
    "公司", "有限", "责任", "人民", "法院", "请求", "规定", "合同",
}


LEGAL_CONCEPTS = {
    "robbery": ("抢劫", "抢劫罪", "暴力劫取", "胁迫劫取"),
    "snatching": ("抢夺", "抢夺罪"),
    "self_defense": ("正当防卫", "防卫过当", "防卫意图", "防卫限度", "学生霸凌"),
    "intentional_injury": ("故意伤害", "故意伤害罪", "互殴", "殴打"),
    "campus_violence": ("校园暴力", "校园欺凌", "学生霸凌"),
}


def legal_concepts(value):
    text = str(value or "")
    return {
        name for name, terms in LEGAL_CONCEPTS.items()
        if any(term in text for term in terms)
    }


def concept_relevance(item, context_text):
    query_concepts = legal_concepts(context_text)
    if not query_concepts:
        return 0.0
    item_text = " ".join((
        item.title or "", item.cause or "", item.keywords or "",
        item.summary or "",
    ))
    return len(query_concepts & legal_concepts(item_text)) / len(query_concepts)


def context_tokens(value):
    tokens = set(re.findall(r"[a-zA-Z0-9]{3,}", str(value or "").lower()))
    for chunk in re.findall(r"[\u4e00-\u9fff]+", str(value or "")):
        if 2 <= len(chunk) <= 6:
            tokens.add(chunk)
        tokens.update(chunk[index:index + 2] for index in range(len(chunk) - 1))
    return {token for token in tokens if token not in STOP_TOKENS}


def case_year(item):
    if item.decision_date:
        return item.decision_date.year
    if item.published_at:
        return item.published_at.year
    match = re.search(r"(20\d{2})年公报", str(item.keywords or ""))
    return int(match.group(1)) if match else None


def lexical_relevance(item, context_text):
    query_tokens = context_tokens(context_text)
    if not query_tokens:
        return 0.0
    item_tokens = context_tokens(" ".join((
        item.title or "", item.cause or "", item.keywords or "",
        item.summary or "", item.dispute_focus or "",
    )))
    return len(query_tokens & item_tokens) / max(1, min(len(query_tokens), 14))


def find_context_cases(context_text, domain, *, limit=6, exclude_ids=()):
    """Return recent cases that actually fit the supplied legal context.

    Old cases survive only when their wording clearly matches the question.
    No popularity fallback is used here because an empty answer is safer than
    an unrelated "real case".
    """
    query = LegalCase.query.filter_by(status="published", verification_status="verified")
    if domain and domain != "other":
        query = query.filter(LegalCase.legal_domain == domain)
    excluded = [int(value) for value in exclude_ids if str(value).isdigit()]
    if excluded:
        query = query.filter(~LegalCase.id.in_(excluded))

    current_year = date.today().year
    required_concepts = legal_concepts(context_text)
    ranked = []
    for item in query.order_by(LegalCase.published_at.desc(), LegalCase.id.desc()).limit(180).all():
        lexical = lexical_relevance(item, context_text)
        concept = concept_relevance(item, context_text)
        same_domain = bool(domain and domain != "other" and item.legal_domain == domain)
        year = case_year(item)
        if required_concepts and concept == 0:
            continue
        if year and year < current_year - 8 and lexical < 0.16 and concept == 0:
            continue
        if not same_domain and lexical < 0.12 and concept == 0:
            continue
        freshness = 0.35 if not year else max(0.0, 1 - max(0, current_year - year) / 12)
        score = lexical * 4 + concept * 3 + (1.6 if same_domain else 0) + freshness
        ranked.append((score, concept, lexical, year or 0, item))
    ranked.sort(key=lambda row: (row[0], row[1], row[2], row[3]), reverse=True)
    return [row[4] for row in ranked[:max(1, min(int(limit), 20))]]
