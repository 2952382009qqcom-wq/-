from core.community.models import CommunityPost, CommunityPostCaseLink
from core.community.serializers import serialize_post
from core.models import db

from .models import CaseRelation, LegalCase
from .matching import find_context_cases


def related_cases(case, limit=4):
    explicit = [
        row for row in LegalCase.query.join(CaseRelation, CaseRelation.related_case_id == LegalCase.id)
        .filter(
            CaseRelation.case_id == case.id,
            LegalCase.status == "published",
            LegalCase.verification_status == "verified",
        )
        .order_by(CaseRelation.relevance_score.desc())
        .limit(limit).all()
    ]
    if len(explicit) >= limit:
        return explicit
    excluded = [case.id] + [item.id for item in explicit]
    fallback = find_context_cases(
        f"{case.title}\n{case.cause}\n{case.dispute_focus}", case.legal_domain,
        limit=limit - len(explicit), exclude_ids=excluded,
    )
    return explicit + fallback


def related_discussions(case, user_id=None, limit=6):
    linked = CommunityPost.query.join(
        CommunityPostCaseLink, CommunityPostCaseLink.post_id == CommunityPost.id
    ).filter(
        CommunityPostCaseLink.case_id == case.id,
        CommunityPost.status == "published",
    ).order_by(CommunityPostCaseLink.relevance_score.desc()).limit(limit).all()
    if len(linked) < limit:
        keywords = [term.strip() for term in case.keywords.split(",") if len(term.strip()) >= 2][:4]
        query = CommunityPost.query.filter_by(status="published")
        if linked:
            query = query.filter(CommunityPost.id.notin_([post.id for post in linked]))
        if keywords:
            from sqlalchemy import or_
            clauses = []
            for keyword in keywords:
                term = f"%{keyword}%"
                clauses.extend((CommunityPost.title.ilike(term), CommunityPost.body.ilike(term)))
            query = query.filter(or_(*clauses))
        linked.extend(query.order_by(CommunityPost.like_count.desc(), CommunityPost.comment_count.desc()).limit(limit - len(linked)).all())
    return [serialize_post(post, user_id) for post in linked]
