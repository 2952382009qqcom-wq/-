import json
import math
import re
from collections import Counter
from datetime import date, datetime, timedelta

from core.cases.models import CaseFavorite, LegalCase
from core.models import db

from .collaborative import load_scores
from .config import ALGORITHM_VERSION, RANKING_WEIGHTS
from .events import domain_weights_for_user
from .models import RecommendationImpression, UserActivityEvent
from .recall import recall_candidates


def _tokens(value):
    tokens = set(re.findall(r"[a-zA-Z0-9]{3,}", str(value or "").lower()))
    for chunk in re.findall(r"[\u4e00-\u9fff]+", str(value or "")):
        if len(chunk) <= 4:
            tokens.add(chunk)
        tokens.update(chunk[index:index + 2] for index in range(len(chunk) - 1))
    return tokens


def _freshness(item):
    if not item.decision_date:
        return 0.2
    return math.exp(-max(0, (date.today() - item.decision_date).days) / 3650)


def _source_trust(item):
    return 1.0 if item.source_type in {"official_court", "guiding_case", "court_gazette"} else 0.45


def _reasons(features, layers, model_version):
    reasons = []
    if features["domain"] >= 0.15:
        reasons.append("与你近期关注的法律领域相关")
    if features["favorite"]:
        reasons.append("与你收藏过的案例同领域")
    if features["text"] >= 0.12 or "keyword" in layers:
        reasons.append("与你当前检索内容相关")
    if features["popularity"] >= 0.45:
        reasons.append("近期较受关注")
    if model_version and features["collaborative"] > 0:
        reasons.append("与你兴趣相似的用户也关注过")
    if not reasons:
        reasons.append("为你探索一个新的法律领域")
    return reasons[:3]


def recommend_cases(user_id, limit=8, context_text="", domain=""):
    limit = max(1, min(int(limit), 30))
    interests = domain_weights_for_user(user_id) if user_id else {}
    recalled = recall_candidates(user_id, domain_weights=interests, context_text=context_text, domain=domain)
    if not recalled:
        return []

    favorite_domains = set()
    if user_id:
        favorite_domains = {row.legal_domain for row in LegalCase.query.join(
            CaseFavorite, CaseFavorite.case_id == LegalCase.id
        ).filter(CaseFavorite.user_id == user_id).all()}

    since = datetime.utcnow() - timedelta(days=30)
    impression_counts = Counter()
    negative_ids = set()
    if user_id:
        impression_counts.update(row.case_id for row in RecommendationImpression.query.filter(
            RecommendationImpression.user_id == user_id,
            RecommendationImpression.created_at >= since,
        ).all())
        negative_ids = {
            int(row.entity_id) for row in UserActivityEvent.query.filter(
                UserActivityEvent.user_id == user_id,
                UserActivityEvent.event_type.in_(("dismiss", "unfavorite")),
            ).all() if str(row.entity_id).isdigit()
        }

    collaborative, model_version = load_scores(user_id) if user_id else ({}, None)
    context_tokens = _tokens(context_text)
    max_views = max([entry["case"].view_count for entry in recalled] + [1])
    ranked = []
    for entry in recalled:
        item = entry["case"]
        domain_score = interests.get(item.legal_domain, 0.0)
        if domain and item.legal_domain == domain:
            domain_score = max(domain_score, 1.0)
        item_tokens = _tokens(" ".join((item.title, item.summary, item.dispute_focus, item.keywords)))
        text_score = len(context_tokens & item_tokens) / max(1, min(len(context_tokens), 12))
        popularity = min(1.0, math.log1p(item.view_count + 2 * item.favorite_count) / math.log1p(max_views + 10))
        features = {
            "domain": domain_score,
            "text": text_score,
            "favorite": 1.0 if item.legal_domain in favorite_domains else 0.0,
            "recency": 1.0 if "recent_activity" in entry["layers"] else 0.0,
            "popularity": popularity,
            "freshness": _freshness(item),
            "source_trust": _source_trust(item),
            "exploration": 1.0 if domain_score == 0 else 0.0,
            "collaborative": max(0.0, min(1.0, collaborative.get(item.id, 0.0))),
            "repeat_exposure": min(1.0, impression_counts[item.id] / 3),
            "negative_feedback": 1.0 if item.id in negative_ids else 0.0,
        }
        score = sum(RANKING_WEIGHTS[name] * value for name, value in features.items())
        ranked.append((score, item, _reasons(features, entry["layers"], model_version)))

    # Greedy domain diversification prevents a single legal domain taking over.
    ranked.sort(key=lambda row: (row[0], row[1].favorite_count, row[1].view_count), reverse=True)
    chosen, domain_counts = [], Counter()
    for score, item, reasons in ranked:
        adjusted = score - max(0, domain_counts[item.legal_domain] - 1) * 0.08
        chosen.append((adjusted, item, reasons))
        domain_counts[item.legal_domain] += 1
    chosen.sort(key=lambda row: row[0], reverse=True)
    chosen = chosen[:limit]

    if user_id:
        for score, item, reasons in chosen:
            db.session.add(RecommendationImpression(
                user_id=user_id, case_id=item.id, score=round(score, 6),
                reason_codes_json=json.dumps(reasons, ensure_ascii=False),
                algorithm_version=ALGORITHM_VERSION,
            ))
        db.session.commit()
    return [(item, round(score, 4), reasons) for score, item, reasons in chosen]
