"""The shared judge/demo account is seeded, pre-approved and model-bound."""

from __future__ import annotations

import os
from unittest import mock


with mock.patch.dict(
    os.environ,
    {
        "DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "test-account-test-secret",
        "AUTO_SEED_REFERENCE_DATA": "1",
        "TEST_ACCOUNT_API_KEY": "sk-test-account-key",
        "TEST_ACCOUNT_MODEL": "deepseek-v4-flash",
    },
):
    import app as app_module

from core.models import User


def test_seeded_test_account_is_ready():
    with app_module.app.app_context():
        user = User.query.filter_by(username=app_module.TEST_ACCOUNT_USERNAME).first()
    assert user is not None
    assert user.is_approved is True
    assert user.is_test_account is True
    # app is imported once per session, so assert against the resolved constants.
    assert user.llm_model == app_module.TEST_ACCOUNT_MODEL
    assert user.llm_api_key == app_module.TEST_ACCOUNT_API_KEY


def test_test_account_default_model_is_deepseek_flash():
    assert app_module.TEST_ACCOUNT_MODEL == "deepseek-v4-flash"


def test_test_account_login_marks_flag_and_hides_quota():
    client = app_module.app.test_client()
    response = client.post("/api/auth/login", json={"username": "mj123", "password": app_module.TEST_ACCOUNT_PASSWORD})
    assert response.status_code == 200
    user = response.get_json()["user"]
    assert user["is_test_account"] is True
    assert user["is_approved"] is True


def test_regular_accounts_are_not_test_accounts():
    client = app_module.app.test_client()
    response = client.post(
        "/api/auth/register", json={"username": "plain-user-xyz", "password": "safe-pass-123"}
    )
    assert response.status_code == 200
    assert response.get_json()["user"]["is_test_account"] is False
