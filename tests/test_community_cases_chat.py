"""Integration coverage for community, verified cases, recommendations and chat."""

from __future__ import annotations

import os
import uuid
from unittest import mock


with mock.patch.dict(
    os.environ,
    {
        "DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "community-module-test-secret",
        "AUTO_SEED_REFERENCE_DATA": "1",
    },
):
    import app as app_module

from core.models import Conversation, ConversationMessage, db
from core.cases.models import CaseCategory, CaseLawReference, LegalCase, LegalCaseCategory


def register(client, prefix):
    username = f"{prefix}-{uuid.uuid4().hex[:8]}"
    response = client.post("/api/auth/register", json={"username": username, "password": "safe-pass-123"})
    assert response.status_code == 200
    return response.get_json()["user"]


def test_anonymous_community_post_comments_and_reactions():
    client = app_module.app.test_client()
    register(client, "community-test")

    categories = client.get("/api/community/categories").get_json()["categories"]
    assert {item["slug"] for item in categories} >= {"campus-rights", "internship-jobs", "renting"}

    created = client.post("/api/community/posts", json={
        "category": "renting",
        "post_type": "legal_help",
        "title": "房东不退押金该怎么办",
        "body": "我的手机号是13800138000，退租后房东一直不退押金。",
        "is_anonymous": True,
    })
    assert created.status_code == 201
    post = created.get_json()["post"]
    assert post["author"]["anonymous"] is True
    assert "id" not in post["author"]
    assert "13800138000" not in post["body"]

    assert client.post(f"/api/community/posts/{post['id']}/like").get_json()["liked"] is True
    assert client.post(f"/api/community/posts/{post['id']}/favorite").get_json()["favorited"] is True
    comment = client.post(f"/api/community/posts/{post['id']}/comments", json={"body": "先保存合同和转账凭证。"})
    assert comment.status_code == 201
    detail = client.get(f"/api/community/posts/{post['id']}").get_json()
    assert detail["post"]["counts"]["comments"] == 1
    assert isinstance(detail["post"]["related_cases"], list)
    assert all(case["legal_domain"] == "housing" for case in detail["post"]["related_cases"])


def test_ai_conversation_becomes_confirmable_anonymous_draft():
    client = app_module.app.test_client()
    user = register(client, "draft-test")
    conversation_id = str(uuid.uuid4())
    with app_module.app.app_context():
        db.session.add(Conversation(id=conversation_id, user_id=user["id"], title="租房咨询"))
        db.session.add(ConversationMessage(
            conversation_id=conversation_id,
            role="user",
            content="房东知道我的电话13900139000，现在不退租房押金怎么办？",
        ))
        db.session.commit()

    preview = client.post("/api/community/ai-draft", json={"conversation_id": conversation_id})
    assert preview.status_code == 200
    draft = preview.get_json()["draft"]
    assert draft["is_anonymous"] is True
    assert draft["post_type"] == "legal_help"
    assert "13900139000" not in draft["body"]

    published = client.post("/api/community/posts", json=draft)
    assert published.status_code == 201
    assert published.get_json()["post"]["is_anonymous"] is True


def test_verified_case_search_favorite_and_personalized_recommendations():
    client = app_module.app.test_client()
    register(client, "case-test")

    result = client.get("/api/cases?q=劳动合同").get_json()
    assert result["cases"]
    case_id = result["cases"][0]["id"]
    detail = client.get(f"/api/cases/{case_id}")
    assert detail.status_code == 200
    case = detail.get_json()["case"]
    assert case["verification_status"] == "verified"
    assert case["source"]["url"].startswith("https://www.court.gov.cn/")
    assert case["dispute_focus"] and case["judgment_reasoning"] and case["ai_plain_language"]

    assert client.post(f"/api/cases/{case_id}/favorite").get_json()["favorited"] is True
    recommendations = client.get("/api/cases/recommendations?limit=4&q=劳动合同").get_json()
    assert recommendations["algorithm"] == "hybrid-v1"
    assert recommendations["cases"]
    assert all(item.get("recommendation", {}).get("reasons") for item in recommendations["cases"])

    disabled = client.put("/api/cases/personalization", json={"enabled": False})
    assert disabled.get_json()["enabled"] is False
    assert client.get("/api/cases/personalization").get_json()["enabled"] is False
    opted_out = client.get("/api/cases/recommendations?limit=4").get_json()
    assert opted_out["personalization_enabled"] is False
    assert opted_out["cases"] == []


def test_case_recommendations_use_current_conversation_and_do_not_popular_fill():
    client = app_module.app.test_client()
    user = register(client, "context-case-test")
    conversation_id = str(uuid.uuid4())
    with app_module.app.app_context():
        db.session.add(Conversation(id=conversation_id, user_id=user["id"], title="租房押金咨询"))
        db.session.add(ConversationMessage(
            conversation_id=conversation_id,
            role="user",
            content="毕业后在校外租房，房东不退押金，也不提供扣款明细。",
        ))
        db.session.commit()

    payload = client.get(f"/api/cases/recommendations?limit=6&conversation_id={conversation_id}").get_json()
    assert payload["context"]["source"] == "conversation"
    assert payload["context"]["domain"] == "housing"
    assert payload["cases"]
    assert all(item["legal_domain"] == "housing" for item in payload["cases"])
    assert all(item["recommendation"]["reasons"][0] == "与当前咨询主题直接相关" for item in payload["cases"])


def test_case_recommendations_follow_latest_robbery_question_instead_of_first_title():
    client = app_module.app.test_client()
    user = register(client, "latest-topic-test")
    conversation_id = str(uuid.uuid4())
    with app_module.app.app_context():
        db.session.add(Conversation(id=conversation_id, user_id=user["id"], title="我被打了怎么办"))
        for content in ("我被打了怎么办", "我能打回去吗", "我被抢劫了怎么办", "抢劫可以定啥罪"):
            db.session.add(ConversationMessage(
                conversation_id=conversation_id,
                role="user",
                content=content,
            ))
            db.session.flush()
        db.session.commit()

    payload = client.get(f"/api/cases/recommendations?limit=6&conversation_id={conversation_id}").get_json()
    assert payload["context"]["domain"] == "criminal"
    assert payload["context"]["label"] == "抢劫可以定啥罪"
    assert payload["cases"]
    assert all(item["legal_domain"] == "criminal" for item in payload["cases"])
    assert all("抢劫" in " ".join((item["title"], item["cause"], " ".join(item["keywords"]), item["summary"])) for item in payload["cases"])


def test_student_audience_only_contains_explicitly_curated_student_cases():
    client = app_module.app.test_client()
    register(client, "student-cases-test")

    categories = client.get("/api/cases/categories").get_json()
    audience = next(item for item in categories["audiences"] if item["slug"] == "student-verified")
    assert audience["count"] >= 11
    payload = client.get("/api/cases?audience=student-verified&per_page=30").get_json()
    assert payload["pagination"]["total"] == audience["count"]
    assert any(item["reference_year"] == 2025 for item in payload["cases"])
    assert any("学生" in item["summary"] or "学校" in item["title"] for item in payload["cases"])


def test_bundled_case_library_is_large_diverse_traceable_and_paginated():
    with app_module.app.app_context():
        rows = LegalCase.query.filter_by(status="published", verification_status="verified").all()
        assert len(rows) == 506
        assert CaseCategory.query.filter_by(is_active=True).count() == 14
        assert CaseCategory.query.filter_by(slug="student-daily", is_active=True).count() == 0
        assert len({row.legal_domain for row in rows}) >= 12
        assert len({row.court_name for row in rows}) >= 115
        assert all(row.source_url.startswith(("https://www.court.gov.cn/", "https://gongbao.court.gov.cn/")) for row in rows)
        assert sum(row.source_type == "official_court_gazette" for row in rows) == 222
        assert all(row.summary and row.dispute_focus and row.judgment_reasoning for row in rows)
        assert all(len(row.source_hash) == 64 for row in rows)
        assert CaseLawReference.query.count() >= 506
        assert LegalCaseCategory.query.count() == 506

    client = app_module.app.test_client()
    register(client, "case-library-test")
    first = client.get("/api/cases?per_page=20&page=1").get_json()
    second = client.get("/api/cases?per_page=20&page=2").get_json()
    assert first["pagination"]["total"] == 506
    assert first["pagination"]["has_next"] is True
    assert len(first["cases"]) == len(second["cases"]) == 20
    assert {item["id"] for item in first["cases"]}.isdisjoint({item["id"] for item in second["cases"]})
    assert all("media" in item for item in first["cases"])

    detail = client.get(f"/api/cases/{first['cases'][0]['id']}").get_json()["case"]
    assert detail["law_references"]
    assert set(detail["media"]) == {"image_url", "image_alt", "image_source_url"}


def test_private_chat_persists_before_delivery_and_enforces_membership():
    first_client = app_module.app.test_client()
    second_client = app_module.app.test_client()
    outsider_client = app_module.app.test_client()
    first = register(first_client, "chat-first")
    second = register(second_client, "chat-second")
    register(outsider_client, "chat-outsider")

    created = first_client.post("/api/chat/threads", json={"user_id": second["id"]})
    assert created.status_code == 201
    thread_id = created.get_json()["thread"]["id"]
    sent = first_client.post(f"/api/chat/threads/{thread_id}/messages", json={"body": "你好，可以交流一下租房证据吗？"})
    assert sent.status_code == 201

    received = second_client.get(f"/api/chat/threads/{thread_id}/messages")
    assert received.status_code == 200
    assert received.get_json()["messages"][-1]["body"].startswith("你好")
    assert outsider_client.get(f"/api/chat/threads/{thread_id}/messages").status_code == 404
    assert first["id"] != second["id"]

    first_socket = app_module.socketio.test_client(
        app_module.app, flask_test_client=first_client, namespace="/chat"
    )
    second_socket = app_module.socketio.test_client(
        app_module.app, flask_test_client=second_client, namespace="/chat"
    )
    assert first_socket.is_connected("/chat") and second_socket.is_connected("/chat")
    first_socket.emit("join_thread", {"thread_id": thread_id}, namespace="/chat")
    second_socket.emit("join_thread", {"thread_id": thread_id}, namespace="/chat")
    second_socket.get_received("/chat")
    first_socket.emit(
        "send_message",
        {"thread_id": thread_id, "body": "这条消息通过实时通道发送。"},
        namespace="/chat",
    )
    events = second_socket.get_received("/chat")
    delivered = [event for event in events if event["name"] == "chat_message"]
    assert delivered and delivered[-1]["args"][0]["body"] == "这条消息通过实时通道发送。"
    first_socket.disconnect(namespace="/chat")
    second_socket.disconnect(namespace="/chat")
