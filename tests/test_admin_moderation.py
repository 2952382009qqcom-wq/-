"""Coverage for the admin moderation console: banned words, review queue, logs, quota."""

from __future__ import annotations

import os
import uuid
from unittest import mock


with mock.patch.dict(
    os.environ,
    {
        "DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "admin-moderation-test-secret",
        "AUTO_SEED_REFERENCE_DATA": "1",
    },
):
    import app as app_module

from core.models import User, db


def register(client, prefix):
    username = f"{prefix}-{uuid.uuid4().hex[:8]}"
    response = client.post("/api/auth/register", json={"username": username, "password": "safe-pass-123"})
    assert response.status_code == 200
    return response.get_json()["user"]


def make_admin(prefix):
    client = app_module.app.test_client()
    user = register(client, prefix)
    with app_module.app.app_context():
        row = User.query.get(user["id"])
        row.is_admin = True
        db.session.commit()
    return client, user


def add_word(admin_client, word, severity):
    response = admin_client.post("/api/admin/banned-words", json={"word": word, "severity": severity})
    assert response.status_code == 200, response.get_json()
    return response.get_json()["word"]["id"]


def make_post(client, body):
    return client.post("/api/community/posts", json={
        "category": "campus-rights",
        "post_type": "discussion",
        "title": "测试发帖",
        "body": body,
    })


def test_banned_word_library_crud():
    user_client = app_module.app.test_client()
    register(user_client, "bw-user")
    assert user_client.get("/api/admin/banned-words").status_code == 403
    assert user_client.post("/api/admin/banned-words", json={"word": "x", "severity": "low"}).status_code == 403

    admin_client, _ = make_admin("bw-admin")
    word_id = add_word(admin_client, "zzbannedcrudtoken", "high")
    listing = admin_client.get("/api/admin/banned-words").get_json()
    assert any(item["id"] == word_id for item in listing["words"])
    assert set(listing["severities"]) == {"high", "medium", "low"}

    updated = admin_client.put(f"/api/admin/banned-words/{word_id}", json={"severity": "low", "is_active": False})
    assert updated.status_code == 200
    assert updated.get_json()["word"]["severity"] == "low"
    assert updated.get_json()["word"]["is_active"] is False

    assert admin_client.delete(f"/api/admin/banned-words/{word_id}").status_code == 200
    assert admin_client.put(f"/api/admin/banned-words/{word_id}", json={"severity": "low"}).status_code == 404


def test_high_risk_word_rejects_publish():
    admin_client, _ = make_admin("hr-admin")
    word_id = add_word(admin_client, "zzhighrejecttoken", "high")
    try:
        author = app_module.app.test_client()
        register(author, "hr-author")
        response = make_post(author, "这段内容包含 zzhighrejecttoken，应当被拒绝")
        assert response.status_code == 400
        assert "拒绝" in response.get_json()["error"]
    finally:
        admin_client.delete(f"/api/admin/banned-words/{word_id}")


def test_medium_risk_word_enters_review_queue():
    admin_client, _ = make_admin("mr-admin")
    word_id = add_word(admin_client, "zzmediumreviewtoken", "medium")
    try:
        author = app_module.app.test_client()
        register(author, "mr-author")
        response = make_post(author, "这段内容包含 zzmediumreviewtoken，需要人工审核")
        assert response.status_code == 201
        data = response.get_json()
        assert data["review_state"] == "pending"
        post_id = data["post"]["id"]

        queue = admin_client.get("/api/admin/review/queue").get_json()
        target = next(
            item for item in queue["items"]
            if item["target_type"] == "post" and item["target_id"] == str(post_id)
        )
        assert target["severity"] == "medium"
        assert "zzmediumreviewtoken" in target["reason"]

        # 待审内容对普通用户不可见
        public = author.get("/api/community/posts").get_json()["posts"]
        assert all(item["id"] != post_id for item in public)
        assert author.get(f"/api/community/posts/{post_id}").status_code == 404

        approved = admin_client.post(f"/api/admin/review/post/{post_id}", json={"action": "approve"})
        assert approved.status_code == 200
        assert approved.get_json()["content_status"] == "published"
        assert author.get(f"/api/community/posts/{post_id}").status_code == 200
    finally:
        admin_client.delete(f"/api/admin/banned-words/{word_id}")


def test_low_risk_word_warns_but_publishes():
    admin_client, _ = make_admin("lr-admin")
    word_id = add_word(admin_client, "zzlowwarntoken", "low")
    try:
        author = app_module.app.test_client()
        register(author, "lr-author")
        response = make_post(author, "内容包含 zzlowwarntoken，但仍可发布")
        assert response.status_code == 201
        data = response.get_json()
        assert data["review_state"] == "approved"
        assert "zzlowwarntoken" in data["warnings"]
        assert author.get(f"/api/community/posts/{data['post']['id']}").status_code == 200
    finally:
        admin_client.delete(f"/api/admin/banned-words/{word_id}")


def test_reset_quota_clears_usage():
    admin_client, _ = make_admin("quota-admin")
    target_client = app_module.app.test_client()
    target = register(target_client, "quota-user")
    with app_module.app.app_context():
        row = User.query.get(target["id"])
        row.free_api_used = 5
        db.session.commit()

    response = admin_client.post(f"/api/admin/reset-quota/{target['id']}")
    assert response.status_code == 200
    assert response.get_json()["user"]["free_api_used"] == 0


def test_operation_log_records_actor_and_ip():
    admin_client, admin = make_admin("log-admin")
    target_client = app_module.app.test_client()
    target = register(target_client, "log-user")

    assert admin_client.post(f"/api/admin/approve/{target['id']}").status_code == 200
    logs = admin_client.get("/api/admin/logs?action=user_approve").get_json()["logs"]
    entry = next(item for item in logs if item["target_id"] == str(target["id"]))
    assert entry["actor_username"] == admin["username"]
    assert entry["ip"]


def test_report_resolution_records_handler():
    admin_client, admin = make_admin("rep-admin")
    author_client = app_module.app.test_client()
    reporter_client = app_module.app.test_client()
    register(author_client, "rep-author")
    register(reporter_client, "rep-reporter")

    post_id = make_post(author_client, "这条内容会被举报。").get_json()["post"]["id"]
    reporter_client.post("/api/community/reports", json={
        "target_type": "post", "target_id": post_id, "reason": "测试举报",
    })
    reports = admin_client.get("/api/community/moderation/reports").get_json()["reports"]
    report = next(row for row in reports if row["target_id"] == str(post_id))
    assert report["status"] == "pending"

    resolved = admin_client.post(
        f"/api/community/moderation/reports/{report['id']}/resolve", json={"action": "dismiss"}
    )
    assert resolved.status_code == 200
    updated = admin_client.get("/api/community/moderation/reports").get_json()["reports"]
    row = next(item for item in updated if item["id"] == report["id"])
    assert row["status"] == "dismissed"
    assert row["resolved_by"] == admin["username"]
    assert row["resolved_at"]
