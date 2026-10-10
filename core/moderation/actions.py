"""Keep content visibility, review records and search indexing in one transaction."""

from datetime import datetime

from core.models import db
from core.search.indexing import enqueue_index

from .models import PendingReview


def queue_content_review(target_type, target_id, *, severity, reason):
    """Create or refresh the current review; editing must not duplicate the queue."""
    row = PendingReview.query.filter_by(
        target_type=target_type, target_id=str(target_id), status="pending"
    ).order_by(PendingReview.id.desc()).first()
    if row is None:
        row = PendingReview(target_type=target_type, target_id=str(target_id), status="pending")
        db.session.add(row)
    row.severity = severity or "medium"
    row.reason = reason[:240]
    return row


def apply_content_status(target_type, target, next_status, *, reviewer_id=None, resolve_reviews=False):
    """Apply a post/comment status without committing or sending external requests.

    Published posts get a search upsert; hidden/deleted posts get a removal.
    Comment counts change only when visibility changes. With resolve_reviews=True,
    pending reviews are closed as approved for publication, otherwise rejected,
    and retain the acting administrator and processing time.
    """
    if target_type not in {"post", "comment"}:
        raise ValueError("不支持的内容类型")
    if next_status not in {"published", "hidden", "deleted"}:
        raise ValueError("不支持的内容状态")
    previous_status = target.status
    target.status = next_status
    if target_type == "post":
        if next_status == "published":
            enqueue_index("community_post", target.id, {
                "title": target.title,
                "body": target.body,
                "category": target.category.slug,
                "post_type": target.post_type,
                "status": next_status,
            })
        else:
            enqueue_index("community_post", target.id, operation="delete")
    elif previous_status != next_status:
        if previous_status == "published":
            target.post.comment_count = max(0, target.post.comment_count - 1)
        elif next_status == "published":
            target.post.comment_count += 1
    if resolve_reviews:
        review_queries = [PendingReview.query.filter_by(
            target_type=target_type, target_id=str(target.id), status="pending"
        )]
        if target_type == "post" and next_status == "deleted":
            from core.community.models import CommunityComment

            comment_ids = [str(row[0]) for row in db.session.query(CommunityComment.id).filter_by(post_id=target.id).all()]
            if comment_ids:
                review_queries.append(PendingReview.query.filter(
                    PendingReview.target_type == "comment", PendingReview.status == "pending",
                    PendingReview.target_id.in_(comment_ids),
                ))
        resolved_at = datetime.utcnow()
        for query in review_queries:
            for review in query.all():
                review.status = "approved" if next_status == "published" else "rejected"
                review.resolved_by = reviewer_id
                review.resolved_at = resolved_at
    return target
