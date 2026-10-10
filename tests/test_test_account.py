"""Test accounts require explicit secure setup; startup never overwrites them."""
import os
import unittest
import uuid
from unittest import mock

with mock.patch.dict(os.environ, {"DATABASE_URL":"sqlite:///:memory:", "SECRET_KEY":"test-account-offline",
                                  "AUTO_SEED_TEST_ACCOUNT":"0", "LLM_API_KEY":"sk-placeholder-only"}):
    import app as app_module

from core.models import User, db
from werkzeug.security import generate_password_hash, check_password_hash


class TestAccountSafetyTests(unittest.TestCase):
    def setUp(self):
        self.context = app_module.app.app_context()
        self.context.push()
        self.addCleanup(self.context.pop)
        self.assertEqual(db.engine.url.database, ":memory:")
        self.name = "judge-" + uuid.uuid4().hex[:12]
        self.patch = mock.patch.multiple(app_module, TEST_ACCOUNT_USERNAME=self.name,
                                        TEST_ACCOUNT_PASSWORD="offline-test-password-only",
                                        TEST_ACCOUNT_MODEL="deepseek-flash",
                                        TEST_ACCOUNT_BASE_URL="https://api.deepseek.com/v1",
                                        TEST_ACCOUNT_API_KEY="")
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.remove_user)

    def remove_user(self):
        db.session.rollback()
        user = User.query.filter_by(username=self.name).first()
        if user:
            db.session.delete(user)
            db.session.commit()

    def test_secure_account_creation_login_flags_and_model(self):
        user = app_module.ensure_test_account()
        self.assertFalse(user.is_admin)
        self.assertTrue(user.is_test_account)
        self.assertTrue(user.is_approved)
        self.assertEqual(user.llm_model, "deepseek-flash")
        client = app_module.app.test_client()
        response = client.post("/api/auth/login", json={"username":self.name, "password":"offline-test-password-only"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["user"]["ai_unlimited"])
        self.assertEqual(client.get("/api/admin/users").status_code, 403)

    def test_restart_preserves_password_model_and_revocation(self):
        user = app_module.ensure_test_account()
        user.password_hash = generate_password_hash("new-offline-password", method="pbkdf2:sha256:1")
        user.llm_model = "deepseek-v4-pro"
        user.is_approved = False
        db.session.commit()
        app_module.ensure_test_account()
        self.assertTrue(check_password_hash(user.password_hash, "new-offline-password"))
        self.assertEqual(user.llm_model, "deepseek-v4-pro")
        self.assertFalse(user.is_approved)

    def test_existing_ordinary_or_admin_identity_is_not_overwritten(self):
        user = User(username=self.name, password_hash="unchanged-hash", is_admin=False, is_approved=False)
        db.session.add(user)
        db.session.commit()
        with self.assertRaisesRegex(RuntimeError, "不会提权"):
            app_module.ensure_test_account()
        self.assertFalse(user.is_approved)
        self.assertEqual(user.password_hash, "unchanged-hash")
        user.is_admin = True
        db.session.commit()
        with self.assertRaises(RuntimeError):
            app_module.ensure_test_account()

    def test_missing_or_weak_password_does_not_create_account(self):
        for password in ("", "123456"):
            with mock.patch.object(app_module, "TEST_ACCOUNT_PASSWORD", password):
                with self.assertRaisesRegex(RuntimeError, "12"):
                    app_module.ensure_test_account()
        self.assertIsNone(User.query.filter_by(username=self.name).first())


if __name__ == "__main__":
    unittest.main()
