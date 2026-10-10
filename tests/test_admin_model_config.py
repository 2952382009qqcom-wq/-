"""Offline regressions for shared credentials, admin routes and quota display."""
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

from werkzeug.security import generate_password_hash

with mock.patch.dict(os.environ, {
    "DATABASE_URL": "sqlite:///:memory:",
    "SECRET_KEY": "admin-model-offline-test-secret",
    "LLM_API_KEY": "sk-placeholder-test-only",
    "AUTO_INIT_DB": "1",
    "AUTO_SEED_REFERENCE_DATA": "1",
}):
    import app as app_module

from core.models import User, db
from core import llm_client


class AdminModelConfigTests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {
            "LLM_API_KEY": "shared-test-key-not-real",
            "LLM_BASE_URL": "https://api.deepseek.com/v1",
            "LLM_MODEL": "deepseek-flash",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.ids = []
        self.old_config = dict(llm_client._config)
        self.addCleanup(self.restore_config)
        self.addCleanup(self.remove_users)
        self.admin = self.make_user(is_admin=True, is_approved=True)
        self.ordinary = self.make_user(is_admin=False, is_approved=True)

    def restore_config(self):
        llm_client._config.clear()
        llm_client._config.update(self.old_config)
        llm_client._client = None
        llm_client._clients.clear()

    def remove_users(self):
        with app_module.app.app_context():
            db.session.rollback()
            for user_id in self.ids:
                user = db.session.get(User, user_id)
                if user:
                    db.session.delete(user)
            db.session.commit()

    def make_user(self, **fields):
        with app_module.app.app_context():
            self.assertEqual(db.engine.url.database, ":memory:")
            user = User(username="model-test-" + uuid.uuid4().hex[:12],
                        password_hash=generate_password_hash("offline-pass-only", method="pbkdf2:sha256:1"),
                        **fields)
            db.session.add(user)
            db.session.commit()
            self.ids.append(user.id)
            client = app_module.app.test_client()
            with client.session_transaction() as session:
                session["_user_id"] = str(user.id)
                session["_fresh"] = True
            return {"id": user.id, "client": client}

    def test_admin_has_separate_portal_and_global_configuration(self):
        client = self.admin["client"]
        response = client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/admin")
        self.assertEqual(client.get("/admin").status_code, 200)
        self.assertEqual(client.get("/api/config").status_code, 403)
        result = client.get("/api/admin/model-config").get_json()
        self.assertEqual(result["model"], "deepseek-flash")
        self.assertNotIn("api_key", result)
        self.assertNotIn("shared-test-key", str(result))

    def test_ordinary_user_cannot_access_global_configuration(self):
        client = self.ordinary["client"]
        for method, path in (("GET", "/api/admin/model-config"),
                             ("POST", "/api/admin/model-config"),
                             ("POST", "/api/admin/model-config/test")):
            self.assertEqual(client.open(path, method=method, json={}).status_code, 403)
        self.assertNotIn('id="admin-panel"', client.get("/").get_data(as_text=True))

    def test_no_personal_key_cannot_redirect_or_test_shared_key(self):
        client = self.ordinary["client"]
        with mock.patch.object(app_module, "test_llm_connection") as outgoing:
            for path in ("/api/config", "/api/config/test"):
                response = client.post(path, json={"base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"})
                self.assertEqual(response.status_code, 400)
            outgoing.assert_not_called()
        with app_module.app.app_context():
            user = db.session.get(User, self.ordinary["id"])
            user.llm_base_url = "https://attacker.invalid/v1"
            user.llm_model = "untrusted-model"
            db.session.commit()
        with app_module.app.test_request_context("/"):
            user = db.session.get(User, self.ordinary["id"])
            with mock.patch.object(app_module, "current_user", user):
                self.assertEqual(app_module._get_llm_config(), {})
        self.assertEqual(client.get("/api/config").get_json()["base_url"], "https://api.deepseek.com/v1")

    def test_personal_key_stays_personal_and_global_env_is_unchanged(self):
        response = self.ordinary["client"].post("/api/config", json={
            "api_key": "personal-test-key-not-real", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-flash",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(os.environ["LLM_API_KEY"], "shared-test-key-not-real")
        with app_module.app.app_context():
            user = db.session.get(User, self.ordinary["id"])
            self.assertEqual(user.llm_api_key, "personal-test-key-not-real")

    def test_invalid_provider_never_triggers_outbound_call(self):
        with mock.patch.object(app_module, "test_llm_connection") as outgoing:
            response = self.ordinary["client"].post("/api/config/test", json={
                "api_key": "personal-test-key-not-real", "base_url": "http://127.0.0.1:1234/v1", "model": "deepseek-flash",
            })
            self.assertEqual(response.status_code, 400)
            outgoing.assert_not_called()

    def test_shared_save_is_atomic_preserves_other_env_and_existing_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("DATABASE_URL='sqlite:///unchanged.db'\nOTHER='keep'\n", encoding="utf-8")
            with mock.patch.dict(app_module.app.config, {"MODEL_CONFIG_ENV_PATH": str(path)}):
                response = self.admin["client"].post("/api/admin/model-config", json={
                    "api_key": "", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-flash",
                })
            self.assertEqual(response.status_code, 200)
            text = path.read_text(encoding="utf-8")
            self.assertIn("DATABASE_URL='sqlite:///unchanged.db'", text)
            self.assertIn("OTHER='keep'", text)
            self.assertIn("LLM_API_KEY='shared-test-key-not-real'", text)

    def test_failed_shared_save_leaves_active_environment_unchanged(self):
        with mock.patch.object(app_module, "_persist_shared_model_settings", side_effect=OSError("offline test")):
            response = self.admin["client"].post("/api/admin/model-config", json={
                "api_key": "replacement-test-key", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-flash",
            })
        self.assertEqual(response.status_code, 503)
        self.assertEqual(os.environ["LLM_API_KEY"], "shared-test-key-not-real")

    def test_omitted_fields_keep_saved_provider_with_its_key(self):
        config = app_module._validate_model_settings(
            {}, "personal-provider-key-not-real", "https://api.moonshot.cn/v1", "moonshot-v1-8k")
        self.assertEqual(config, ("personal-provider-key-not-real", "https://api.moonshot.cn/v1", "moonshot-v1-8k"))

    def test_approved_test_user_is_unlimited_without_admin_permissions(self):
        client = self.ordinary["client"]
        with app_module.app.app_context():
            user = db.session.get(User, self.ordinary["id"])
            user.free_api_used = 10000
            db.session.commit()
            for _ in range(15):
                with app_module.app.test_request_context("/"), mock.patch.object(app_module, "current_user", user):
                    response = app_module.require_approved(lambda: app_module.jsonify({"ok": True}))()
                    self.assertEqual(response.status_code, 200)
            self.assertEqual(user.free_api_used, 10000)
        info = client.get("/api/auth/status").get_json()["user"]
        self.assertTrue(info["ai_unlimited"])
        self.assertIsNone(info["free_api_remaining"])
        self.assertFalse(info["is_admin"])
        self.assertEqual(client.get("/api/admin/all-users").status_code, 403)


if __name__ == "__main__":
    unittest.main()
