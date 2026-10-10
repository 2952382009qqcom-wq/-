"""Offline checks for the teacher's three-level content governance workflow."""

from types import SimpleNamespace
from unittest import mock

import pytest
from flask import Flask
from flask_login import LoginManager

from core.admin.routes import admin_bp
from core.community.models import CommunityCategory, CommunityComment, CommunityPost, CommunityReport
from core.community.routes import community_bp
from core.extensions import limiter
from core.models import User, db
from core.moderation.models import AdminActionLog, BannedWord, PendingReview
from core.recommendations.models import SearchIndexOutbox


@pytest.fixture
def site():
    # This small in-memory app does not read deployed DB/model configuration.
    app = Flask("teacher_moderation_test")
    app.config.update(
        TESTING=True,
        SECRET_KEY="offline-moderation-only",
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        RATELIMIT_ENABLED=False,
    )
    db.init_app(app)
    limiter.init_app(app)
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.register_blueprint(community_bp)
    app.register_blueprint(admin_bp)
    with app.app_context():
        db.create_all()
        author = User(username="offline-author", password_hash="unused")
        admin = User(username="offline-admin", password_hash="unused", is_admin=True)
        db.session.add_all([author, admin, CommunityCategory(slug="campus-rights", name="校园权益")])
        db.session.add_all([
            BannedWord(word="zzteacherhigh", severity="high"),
            BannedWord(word="zzteachermedium", severity="medium"),
            BannedWord(word="zzteacherlow", severity="low"),
            BannedWord(word="zzteacherinactive", severity="high", is_active=False),
        ])
        db.session.commit()
        author_id, admin_id = author.id, admin.id

    def client_for(user_id):
        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True
        return client

    with mock.patch("core.search.indexing.get_search_client", return_value=None):
        yield SimpleNamespace(
            app=app, author=client_for(author_id), admin=client_for(admin_id),
            author_id=author_id, admin_id=admin_id,
        )
    with app.app_context():
        db.session.remove()
        db.drop_all()


def publish(site, body="正常的校园法律求助", title="测试求助"):
    return site.author.post("/api/community/posts", json={
        "category": "campus-rights", "post_type": "legal_help", "title": title, "body": body,
    })


def public_post_ids(site):
    return {row["id"] for row in site.author.get("/api/community/posts").get_json()["posts"]}


@pytest.mark.parametrize("target_type", ["post", "comment"])
@pytest.mark.parametrize("severity,expected_code", [("high", 400), ("medium", 201), ("low", 201)])
def test_post_and_comment_follow_three_levels(site, target_type, severity, expected_code):
    word = "zzteacher" + severity
    if target_type == "post":
        response = publish(site, f"法律问题 {word.upper()}")
        post_id = None
    else:
        post_id = publish(site).get_json()["post"]["id"]
        response = site.author.post(f"/api/community/posts/{post_id}/comments", json={"body": f"回复 {word}"})
    assert response.status_code == expected_code
    payload = response.get_json()
    with site.app.app_context():
        query = CommunityPost.query if target_type == "post" else CommunityComment.query
        if severity == "high":
            assert "拒绝发布" in payload["error"]
            assert query.count() == 0
            assert PendingReview.query.count() == 0
            return
        content = payload[target_type]
        target = db.session.get(CommunityPost if target_type == "post" else CommunityComment, content["id"])
        assert word in payload["warnings"]
        assert target.status == ("hidden" if severity == "medium" else "published")
        assert payload["review_state"] == ("pending" if severity == "medium" else "approved")
        review = PendingReview.query.filter_by(target_type=target_type, target_id=str(target.id)).first()
        if severity == "medium":
            assert review.status == "pending" and review.severity == "medium"
            assert word in review.reason
        else:
            assert review is None
        if target_type == "comment":
            assert db.session.get(CommunityPost, post_id).comment_count == (0 if severity == "medium" else 1)
    if target_type == "post":
        assert (content["id"] in public_post_ids(site)) == (severity == "low")


def test_highest_severity_wins_and_disabled_words_are_ignored(site):
    assert publish(site, "zzteacherlow zzteachermedium zzteacherhigh").status_code == 400
    pending = publish(site, "zzteacherlow zzteachermedium").get_json()
    assert pending["review_state"] == "pending"
    assert set(pending["warnings"]) == {"zzteacherlow", "zzteachermedium"}
    ignored = publish(site, "zzteacherinactive").get_json()
    assert ignored["review_state"] == "approved" and ignored["warnings"] == []


def test_edit_screening_rejects_atomically_and_warns_on_low_risk(site):
    post_id = publish(site).get_json()["post"]["id"]
    low = site.author.patch(f"/api/community/posts/{post_id}", json={"body": "提示 zzteacherlow"})
    assert low.status_code == 200
    assert low.get_json()["review_state"] == "approved"
    assert low.get_json()["warnings"] == ["zzteacherlow"]
    assert post_id in public_post_ids(site)
    with site.app.app_context():
        initial = db.session.get(CommunityPost, post_id)
        before = (initial.title, initial.body, initial.help_status)
        outbox_count = SearchIndexOutbox.query.count()
    high = site.author.patch(f"/api/community/posts/{post_id}", json={
        "title": "不能保存的修改标题", "body": "拒绝 zzteacherhigh", "help_status": "resolved",
    })
    assert high.status_code == 400
    with site.app.app_context():
        unchanged = db.session.get(CommunityPost, post_id)
        assert (unchanged.title, unchanged.body, unchanged.help_status) == before
        assert unchanged.status == "published"
        assert SearchIndexOutbox.query.count() == outbox_count


def test_medium_edit_hides_refreshes_review_and_cannot_self_release(site):
    post_id = publish(site).get_json()["post"]["id"]
    url = f"/api/community/posts/{post_id}"
    edited = site.author.patch(url, json={"title": "zzteachermedium 新标题"}).get_json()
    assert edited["review_state"] == "pending"
    assert post_id not in public_post_ids(site)
    assert site.author.patch(url, json={"body": "zzteachermedium 修改正文"}).status_code == 200
    cleaned = site.author.patch(url, json={"title": "修改后的正常标题", "body": "已移除敏感词"}).get_json()
    assert cleaned["review_state"] == "pending"
    assert post_id not in public_post_ids(site)
    with site.app.app_context():
        assert PendingReview.query.filter_by(target_type="post", target_id=str(post_id), status="pending").count() == 1
        review = PendingReview.query.filter_by(target_id=str(post_id)).one()
        assert "等待管理员复核" in review.reason
        newest_index_task = SearchIndexOutbox.query.order_by(SearchIndexOutbox.id.desc()).first()
        assert newest_index_task.operation == "delete"


def test_moderator_hold_remains_after_author_edits(site):
    post_id = publish(site).get_json()["post"]["id"]
    assert site.admin.post(f"/api/community/moderation/content/post/{post_id}", json={"action": "hide"}).status_code == 200
    edited = site.author.patch(f"/api/community/posts/{post_id}", json={"body": "已修正问题"}).get_json()
    assert edited["review_state"] == "pending"
    assert post_id not in public_post_ids(site)


@pytest.mark.parametrize("action,status", [("approve", "published"), ("reject", "hidden"), ("delete", "deleted")])
def test_admin_review_sees_full_body_reason_and_records_decision(site, action, status):
    body = "详细事实。" * 80 + " zzteachermedium"
    post_id = publish(site, body).get_json()["post"]["id"]
    assert site.author.get("/api/admin/review/queue").status_code == 403
    queue = site.admin.get("/api/admin/review/queue").get_json()["items"]
    item = next(row for row in queue if row["target_id"] == str(post_id))
    assert item["body"] == body and "zzteachermedium" in item["reason"]
    response = site.admin.post(f"/api/admin/review/post/{post_id}", json={"action": action}, environ_overrides={"REMOTE_ADDR": "203.0.113.17"})
    assert response.status_code == 200
    assert response.get_json()["content_status"] == status
    with site.app.app_context():
        review = PendingReview.query.filter_by(target_type="post", target_id=str(post_id)).one()
        assert review.status == ("approved" if action == "approve" else "rejected")
        assert review.resolved_by == site.admin_id and review.resolved_at is not None
        log = AdminActionLog.query.filter_by(action=f"review_{action}", target_id=str(post_id)).one()
        assert log.actor_username == "offline-admin" and log.created_at is not None
        assert log.ip == "203.0.113.17"
        task = SearchIndexOutbox.query.order_by(SearchIndexOutbox.id.desc()).first()
        assert task.operation == ("upsert" if action == "approve" else "delete")
    # An old queue button must never republish a resolved/deleted item.
    assert site.admin.post(f"/api/admin/review/post/{post_id}", json={"action": "approve"}).status_code == 409


@pytest.mark.parametrize("admin_delete", [False, True])
def test_direct_deletion_closes_review_and_cannot_be_revived(site, admin_delete):
    post_id = publish(site, "zzteachermedium").get_json()["post"]["id"]
    client = site.admin if admin_delete else site.author
    assert client.delete(f"/api/community/posts/{post_id}").status_code == 200
    assert site.admin.post(f"/api/admin/review/post/{post_id}", json={"action": "approve"}).status_code == 409
    assert site.author.patch(f"/api/community/posts/{post_id}", json={"body": "不应复活"}).status_code == 400
    with site.app.app_context():
        review = PendingReview.query.filter_by(target_type="post", target_id=str(post_id)).one()
        assert review.status == "rejected" and review.resolved_at is not None
        assert review.resolved_by == (site.admin_id if admin_delete else None)
        log = AdminActionLog.query.filter_by(action="community_moderate", target_id=str(post_id)).first()
        assert bool(log) == admin_delete


def test_comment_count_changes_once_for_hide_restore_and_delete(site):
    post_id = publish(site).get_json()["post"]["id"]
    comment_id = site.author.post(f"/api/community/posts/{post_id}/comments", json={"body": "正常评论"}).get_json()["comment"]["id"]
    for action, expected_count in [("hide", 0), ("hide", 0), ("restore", 1), ("restore", 1), ("delete", 0), ("delete", 0)]:
        response = site.admin.post(f"/api/community/moderation/content/comment/{comment_id}", json={"action": action})
        assert response.status_code == 200
        with site.app.app_context():
            assert db.session.get(CommunityPost, post_id).comment_count == expected_count


@pytest.mark.parametrize("action,status,count", [("approve", "published", 1), ("reject", "hidden", 0), ("delete", "deleted", 0)])
def test_admin_comment_review_updates_visibility_count_and_handler(site, action, status, count):
    post_id = publish(site).get_json()["post"]["id"]
    comment_id = site.author.post(f"/api/community/posts/{post_id}/comments", json={"body": "待审回复 zzteachermedium"}).get_json()["comment"]["id"]
    assert site.admin.post(f"/api/admin/review/comment/{comment_id}", json={"action": action}).status_code == 200
    assert site.admin.post(f"/api/admin/review/comment/{comment_id}", json={"action": "approve"}).status_code == 409
    with site.app.app_context():
        assert db.session.get(CommunityComment, comment_id).status == status
        assert db.session.get(CommunityPost, post_id).comment_count == count
        review = PendingReview.query.filter_by(target_type="comment", target_id=str(comment_id)).one()
        assert review.resolved_by == site.admin_id and review.resolved_at is not None


def test_deleting_parent_post_closes_its_pending_comment_reviews(site):
    post_id = publish(site).get_json()["post"]["id"]
    comment_id = site.author.post(f"/api/community/posts/{post_id}/comments", json={"body": "待审回复 zzteachermedium"}).get_json()["comment"]["id"]
    assert site.admin.delete(f"/api/community/posts/{post_id}").status_code == 200
    assert site.admin.get("/api/admin/review/queue").get_json()["items"] == []
    assert site.admin.post(f"/api/admin/review/comment/{comment_id}", json={"action": "approve"}).status_code == 409
    with site.app.app_context():
        review = PendingReview.query.filter_by(target_type="comment", target_id=str(comment_id)).one()
        assert review.status == "rejected" and review.resolved_by == site.admin_id
        assert review.resolved_at is not None


def test_admin_edit_audit_only_records_successful_changes(site):
    post_id = publish(site).get_json()["post"]["id"]
    url = f"/api/community/posts/{post_id}"
    assert site.admin.patch(url, json={"body": "管理员修正正文"}).status_code == 200
    assert site.admin.patch(url, json={"body": "拒绝修改 zzteacherhigh"}).status_code == 400
    with site.app.app_context():
        log = AdminActionLog.query.filter_by(action="community_edit", target_id=str(post_id)).one()
        assert log.actor_id == site.admin_id and log.ip
        assert db.session.get(CommunityPost, post_id).body == "管理员修正正文"


def test_report_records_handler_time_and_repeated_processing_preserves_history(site):
    post_id = publish(site).get_json()["post"]["id"]
    reported = site.author.post("/api/community/reports", json={
        "target_type": "post", "target_id": f"00{post_id}", "reason": "内容不当", "detail": "举报说明",
    })
    assert reported.status_code == 201
    report = site.admin.get("/api/community/moderation/reports").get_json()["reports"][0]
    assert report["status"] == "pending" and report["target_id"] == str(post_id)
    url = f"/api/community/moderation/reports/{report['id']}/resolve"
    assert site.author.post(url, json={"action": "hide"}).status_code == 403
    assert site.admin.post(url, json={"action": "hide"}).status_code == 200
    updated = site.admin.get("/api/community/moderation/reports").get_json()["reports"][0]
    assert updated["status"] == "resolved"
    assert updated["resolved_by"] == "offline-admin" and updated["resolved_by_id"] == site.admin_id
    assert updated["resolved_at"]
    with site.app.app_context():
        initial_time = db.session.get(CommunityReport, report["id"]).resolved_at
    assert site.admin.post(url, json={"action": "dismiss"}).status_code == 409
    with site.app.app_context():
        row = db.session.get(CommunityReport, report["id"])
        assert row.status == "resolved" and row.resolved_at == initial_time
        assert AdminActionLog.query.filter_by(action="report_resolve").count() == 1


def test_reports_cannot_target_missing_or_hidden_content(site):
    assert site.author.post("/api/community/reports", json={
        "target_type": "post", "target_id": 99999, "reason": "不存在",
    }).status_code == 404
    post_id = publish(site, "zzteachermedium").get_json()["post"]["id"]
    assert site.author.post("/api/community/reports", json={
        "target_type": "post", "target_id": post_id, "reason": "待审内容不能公开操作",
    }).status_code == 404


def test_forwarding_headers_cannot_forge_admin_audit_ip(site):
    response = site.admin.post("/api/admin/banned-words", json={
        "word": "zzteacheripcheck", "severity": "low",
    }, headers={
        "X-Forwarded-For": "198.51.100.99, 198.51.100.100",
        "X-Real-IP": "198.51.100.101",
        "Forwarded": "for=198.51.100.102",
    }, environ_overrides={"REMOTE_ADDR": "203.0.113.22"})
    assert response.status_code == 200
    with site.app.app_context():
        log = AdminActionLog.query.filter_by(action="banned_word_create", target_id="zzteacheripcheck").one()
        assert log.actor_id == site.admin_id and log.actor_username == "offline-admin"
        assert log.ip == "203.0.113.22" and log.created_at is not None
