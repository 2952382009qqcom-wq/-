import json
import math
import re
from datetime import date

from core.models import db
from core.cases.models import CaseFavorite, LegalCase

from .events import domain_weights_for_user
from .models import RecommendationImpression


def _tokens(value):
    return set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]{3,}", str(value or "").lower()))


def _freshness(case):
    if not case.decision_date:
        return 0.2
    age = max(0, (date.today() - case.decision_date).days)
    return 0.25 * math.exp(-age / 3650)


def _serialize_reason(domain_affinity, favorite_bonus, popularity):
    reasons = []
    if domain_affinity >= 0.15:
        reasons.append("与你近期关注的法律领域相关")
    if favorite_bonus:
        reasons.append("与你收藏过的案例同领域")
    if popularity > 0.15:
        reasons.append("近期较受关注")
    return reasons or ["为你探索一个新的法律领域"]


def recommend_cases(user_id, limit=8, context_text="", domain=""):
    limit = max(1, min(int(limit), 30))
    cases = LegalCase.query.filter_by(status="published", verification_status="verified").all()
    if not cases:
        return []
    weights = domain_weights_for_user(user_id) if user_id else {}
    favorite_domains = {
        item.legal_domain
        for item in LegalCase.query.join(CaseFavorite, CaseFavorite.case_id == LegalCase.id)
        .filter(CaseFavorite.user_id == user_id)
        .all()
    } if user_id else set()
    context_tokens = _tokens(context_text)
    max_views = max([case.view_count for case in cases] + [1])
    ranked = []
    for item in cases:
        domain_affinity = weights.get(item.legal_domain, 0.0)
        if domain and item.legal_domain == domain:
            domain_affinity = max(domain_affinity, 0.8)
        candidate_tokens = _tokens(" ".join((item.title, item.summary, item.dispute_focus, item.keywords)))
        content_score = len(context_tokens & candidate_tokens) / max(1, min(len(context_tokens), 12))
        favorite_bonus = 0.18 if item.legal_domain in favorite_domains else 0.0
        popularity = min(1.0, math.log1p(item.view_count + 2 * item.favorite_count) / math.log1p(max_views + 10))
        score = 0.43 * domain_affinity + 0.27 * content_score + favorite_bonus + 0.08 * popularity + _freshness(item)
        reasons = _serialize_reason(domain_affinity, favorite_bonus, popularity)
        ranked.append((score, item, reasons))
    ranked.sort(key=lambda row: (row[0], row[1].favorite_count, row[1].view_count), reverse=True)
    chosen = ranked[:limit]
    if user_id:
        for score, item, reasons in chosen:
            db.session.add(RecommendationImpression(
                user_id=user_id,
                case_id=item.id,
                score=round(score, 6),
                reason_codes_json=json.dumps(reasons, ensure_ascii=False),
            ))
        db.session.commit()
    return [(item, round(score, 4), reasons) for score, item, reasons in chosen]
