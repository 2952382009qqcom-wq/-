from core.cases.serializers import serialize_case_card

from .models import CommunityCommentLike, CommunityPostFavorite, CommunityPostLike


def _display_author(author, *, anonymous=False, is_owner=False):
    if anonymous:
        return {"name": "匿名同学", "anonymous": True, "is_owner": is_owner}
    if author is None:
        return {"name": "已注销用户", "anonymous": False, "is_owner": is_owner}
    return {"id": author.id, "name": author.username, "anonymous": False, "is_owner": is_owner}


def serialize_post(post, user_id=None, *, detail=False, related_cases=None):
    liked = bool(user_id and CommunityPostLike.query.filter_by(user_id=user_id, post_id=post.id).first())
    favorited = bool(user_id and CommunityPostFavorite.query.filter_by(user_id=user_id, post_id=post.id).first())
    payload = {
        "id": post.id,
        "title": post.title,
        "body": post.body if detail else post.body[:220] + ("…" if len(post.body) > 220 else ""),
        "post_type": post.post_type,
        "help_status": post.help_status,
        "is_anonymous": post.is_anonymous,
        "category": {"id": post.category.id, "slug": post.category.slug, "name": post.category.name},
        "author": _display_author(post.author, anonymous=post.is_anonymous, is_owner=bool(user_id and post.author_id == user_id)),
        "counts": {
            "views": post.view_count,
            "likes": post.like_count,
            "comments": post.comment_count,
            "favorites": post.favorite_count,
        },
        "viewer": {"liked": liked, "favorited": favorited, "can_edit": bool(user_id and post.author_id == user_id)},
        "created_at": post.created_at.isoformat(timespec="minutes"),
        "updated_at": post.updated_at.isoformat(timespec="minutes"),
    }
    if detail:
        payload["related_cases"] = [serialize_case_card(case, user_id) for case in (related_cases or [])]
    return payload


def serialize_comment(comment, post, user_id=None):
    liked = bool(user_id and CommunityCommentLike.query.filter_by(user_id=user_id, comment_id=comment.id).first())
    is_post_author = bool(post.author_id and comment.author_id == post.author_id)
    anonymous = bool(post.is_anonymous and is_post_author)
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "parent_id": comment.parent_id,
        "body": comment.body,
        "author": _display_author(comment.author, anonymous=anonymous, is_owner=is_post_author),
        "reply_to": comment.reply_to_user.username if comment.reply_to_user and not anonymous else "",
        "like_count": comment.like_count,
        "liked": liked,
        "can_edit": bool(user_id and comment.author_id == user_id),
        "created_at": comment.created_at.isoformat(timespec="minutes"),
    }
