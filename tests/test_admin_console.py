"""Coverage for the separated admin console (/admin)."""

from __future__ import annotations

import os
import uuid
from unittest import mock


with mock.patch.dict(
    os.environ,
    {
        "DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "admin-console-test-secret",
        "AUTO_SEED_REFERENCE_DATA": "1",
    },
):
    import app as app_module

from core.models import User, db
from core.conversation import add_message, get_or_create_conversation


def register(client, prefix):
    username = f"{prefix}-{uuid.uuid4().hex[:8]}"
    response = client.post("/api/auth/register", json={"username": username, "password": "safe-pass-123"})
    assert response.status_code == 200
    return response.get_json()["user"]


def make_admin(client, prefix):
    user = register(client, prefix)
    with app_module.app.app_context():
        row = User.query.get(user["id"])
        row.is_admin = True
        db.session.commit()
    return user


def test_admin_console_page_and_home_redirect():
    admin_client = app_module.app.test_client()
    make_admin(admin_client, "console-admin")

    page = admin_client.get("/admin")
    assert page.status_code == 200
    assert "管理控制台" in page.get_data(as_text=True)

    # 管理员被从用户首页剥离到独立控制台
    home = admin_client.get("/")
    assert home.status_code == 302
    assert "/admin" in home.headers["Location"]

    # 普通用户仍走原有首页，行为不变
    user_client = app_module.app.test_client()
    register(user_client, "console-user")
    plain_home = user_client.get("/")
    assert plain_home.status_code == 200
    assert "管理控制台" not in plain_home.get_data(as_text=True)


def test_case_crud_requires_admin_and_persists():
    user_client = app_module.app.test_client()
    register(user_client, "case-denied")
    assert user_client.get("/api/admin/cases").status_code == 403

    admin_client = app_module.app.test_client()
    make_admin(admin_client, "case-admin")

    created = admin_client.post("/api/admin/cases", json={
        "title": "测试买卖合同纠纷案",
        "summary": "原被告因货款支付发生争议。",
        "dispute_focus": "货款是否已经支付。",
        "judgment_result": "判令被告支付货款。",
        "judgment_reasoning": "证据足以证明欠款事实。",
        "ai_plain_language": "法院认为欠钱要还。",
        "source_publisher": "测试法院",
        "source_url": "https://example.com/case",
        "keywords": "买卖合同,货款",
    })
    assert created.status_code == 200
    case_id = created.get_json()["id"]

    listing = admin_client.get("/api/admin/cases").get_json()
    assert any(item["id"] == case_id for item in listing["cases"])

    # 默认以「已发布 + 已核验」创建，普通用户案例接口立即可见
    assert user_client.get(f"/api/cases/{case_id}").status_code == 200

    updated = admin_client.put(f"/api/admin/cases/{case_id}", json={"title": "更新后的案由", "status": "hidden"})
    assert updated.status_code == 200
    detail = admin_client.get(f"/api/admin/cases/{case_id}").get_json()["case"]
    assert detail["title"] == "更新后的案由"
    assert detail["status"] == "hidden"

    assert admin_client.delete(f"/api/admin/cases/{case_id}").status_code == 200
    assert admin_client.get(f"/api/admin/cases/{case_id}").status_code == 404


def test_audit_exposes_only_redacted_content():
    user_client = app_module.app.test_client()
    user = register(user_client, "audit-user")
    with app_module.app.app_context():
        conversation, _ = get_or_create_conversation(user["id"], title_hint="关于欠款")
        add_message(conversation, "user", "我的手机号是13800138000，对方一直欠我钱。")
        conversation_id = conversation.id

    assert user_client.get("/api/admin/audit/conversations").status_code == 403

    admin_client = app_module.app.test_client()
    make_admin(admin_client, "audit-admin")
    listing = admin_client.get("/api/admin/audit/conversations").get_json()
    assert any(item["id"] == conversation_id for item in listing["conversations"])

    detail = admin_client.get(f"/api/admin/audit/conversations/{conversation_id}").get_json()
    assert detail["redacted"] is True
    content = "".join(message["content"] for message in detail["messages"])
    assert "13800138000" not in content
    assert "[手机号_" in content


def test_system_overview_fields():
    admin_client = app_module.app.test_client()
    make_admin(admin_client, "system-admin")
    data = admin_client.get("/api/admin/system").get_json()
    assert "version" in data
    assert set(data["components"]) == {"database", "external_model", "ocr"}
    assert {"users", "cases", "posts", "conversations"} <= set(data["counts"])
