"""No deployment or live credentials: startup safety uses in-memory SQLite."""
import os
import unittest
import uuid
from unittest import mock

with mock.patch.dict(os.environ, {
    "DATABASE_URL": "sqlite:///:memory:", "SECRET_KEY": "bootstrap-offline-test",
    "LLM_API_KEY": "sk-placeholder-test-only", "AUTO_INIT_DB": "1", "AUTO_SEED_REFERENCE_DATA": "1",
}):
    import app as app_module

from core.models import User, db
from werkzeug.security import generate_password_hash, check_password_hash


class BootstrapSafetyTests(unittest.TestCase):
    def setUp(self):
        self.context = app_module.app.app_context()
        self.context.push()
        self.addCleanup(self.context.pop)
        self.assertEqual(db.engine.url.database, ":memory:")
        self.assertIsNone(User.query.filter_by(is_admin=True).first())
        self.ids = []
        self.addCleanup(self.remove_users)

    def remove_users(self):
        db.session.rollback()
        for user_id in self.ids:
            user = db.session.get(User, user_id)
            if user:
                db.session.delete(user)
        db.session.commit()

    def make_user(self, username, admin=False):
        user = User(username=username, is_admin=admin, is_approved=admin,
                    password_hash=generate_password_hash("saved-new-password", method="pbkdf2:sha256:1"))
        db.session.add(user)
        db.session.commit()
        self.ids.append(user.id)
        return user

    def test_restart_preserves_renamed_admin_and_password(self):
        user = self.make_user("renamed-admin-" + uuid.uuid4().hex[:8], admin=True)
        with mock.patch.dict(os.environ, {"ADMIN_USERNAME": "admin", "ADMIN_PASSWORD": "obsolete-initial-pass"}):
            result, created = app_module.ensure_initial_administrator()
        self.assertFalse(created)
        self.assertEqual(result.id, user.id)
        self.assertTrue(result.username.startswith("renamed-admin-"))
        self.assertTrue(check_password_hash(result.password_hash, "saved-new-password"))

    def test_reserved_username_is_never_promoted(self):
        name = "reserved-" + uuid.uuid4().hex[:8]
        user = self.make_user(name)
        with mock.patch.dict(os.environ, {"ADMIN_USERNAME": name, "ADMIN_PASSWORD": "strong-test-password"}):
            with self.assertRaisesRegex(RuntimeError, "普通账号"):
                app_module.ensure_initial_administrator()
        self.assertFalse(user.is_admin)
        self.assertFalse(user.is_approved)

    def test_first_admin_rejects_empty_password_but_accepts_short(self):
        with mock.patch.dict(os.environ, {"ADMIN_USERNAME": "fresh-empty-admin", "ADMIN_PASSWORD": ""}):
            with self.assertRaisesRegex(RuntimeError, "ADMIN_PASSWORD"):
                app_module.ensure_initial_administrator()
        self.assertIsNone(User.query.filter_by(is_admin=True).first())
        name = "fresh-short-" + uuid.uuid4().hex[:8]
        with mock.patch.dict(os.environ, {"ADMIN_USERNAME": name, "ADMIN_PASSWORD": "short"}):
            user, created = app_module.ensure_initial_administrator()
            self.ids.append(user.id)
        self.assertTrue(created)
        self.assertTrue(check_password_hash(user.password_hash, "short"))

    def test_first_admin_creation_is_idempotent(self):
        name = "first-" + uuid.uuid4().hex[:8]
        with mock.patch.dict(os.environ, {"ADMIN_USERNAME": name, "ADMIN_PASSWORD": "strong-test-password"}):
            user, created = app_module.ensure_initial_administrator()
            self.ids.append(user.id)
            second, recreated = app_module.ensure_initial_administrator()
        self.assertTrue(created)
        self.assertFalse(recreated)
        self.assertEqual(second.id, user.id)
        self.assertTrue(user.is_admin)


if __name__ == "__main__":
    unittest.main()
