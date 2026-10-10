"""Role-separated login and administrator account maintenance, entirely offline."""

import os
import unittest
import uuid
from unittest import mock

from werkzeug.security import check_password_hash, generate_password_hash


TEST_ENV = {
    "DATABASE_URL": "sqlite:///:memory:",
    "SECRET_KEY": "account-separation-test-secret-only",
    "LLM_API_KEY": "sk-placeholder-account-separation-tests",
    "LLM_BASE_URL": "http://127.0.0.1:9/v1",
    "AUTO_INIT_DB": "1",
    "AUTO_SEED_REFERENCE_DATA": "1",
    "RATELIMIT_STORAGE_URI": "memory://",
    "SOCKETIO_REDIS_URL": "",
    "FREE_API_LIMIT": "10",
}

# Apply the SQLite and placeholder settings before app import, matching the
# existing integration tests. Never load or mutate the production database.
with mock.patch.dict(os.environ, TEST_ENV):
    import app as app_module

from core.models import User, db


class AccountSeparationTests(unittest.TestCase):
    password = "Account-test-password-123"

    def setUp(self):
        self.environment = mock.patch.dict(os.environ, TEST_ENV)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = app_module.app.test_client()
        self.created_ids = []
        self.addCleanup(self.remove_test_users)
        with app_module.app.app_context():
            self.assertEqual(db.engine.url.database, ":memory:")

    def remove_test_users(self):
        with app_module.app.app_context():
            db.session.rollback()
            for user_id in self.created_ids:
                user = db.session.get(User, user_id)
                if user is not None:
                    db.session.delete(user)
            db.session.commit()

    def make_user(self, **attributes):
        with app_module.app.app_context():
            user = User(
                username=f"account-test-{uuid.uuid4().hex[:12]}",
                password_hash=generate_password_hash(self.password),
                **attributes,
            )
            db.session.add(user)
            db.session.commit()
            self.created_ids.append(user.id)
            return {"id": user.id, "username": user.username}

    def login(self, user, admin=False, client=None, password=None):
        return (client or self.client).post(
            "/api/admin/login" if admin else "/api/auth/login",
            json={"username": user["username"], "password": password or self.password},
        )

    def status_user(self, client=None):
        return (client or self.client).get("/api/auth/status").get_json()

    def test_each_login_rejects_the_other_role_without_creating_a_session(self):
        admin = self.make_user(is_admin=True)
        ordinary = self.make_user(is_admin=False, is_approved=True)
        for user, admin_entry, code in (
            (admin, False, "ADMIN_LOGIN_REQUIRED"),
            (ordinary, True, "ADMIN_ACCOUNT_REQUIRED"),
        ):
            with self.subTest(admin_entry=admin_entry):
                response = self.login(user, admin=admin_entry)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.get_json()["code"], code)
                self.assertFalse(self.status_user()["authenticated"])
                incorrect = self.login(user, admin=admin_entry, password="incorrect-password")
                self.assertEqual(incorrect.status_code, 401)
                self.assertNotIn("code", incorrect.get_json())

    def test_rejected_login_keeps_the_existing_account_session(self):
        admin = self.make_user(is_admin=True)
        ordinary = self.make_user(is_admin=False, is_approved=True)
        self.assertEqual(self.login(ordinary).status_code, 200)
        self.assertEqual(self.login(admin).status_code, 403)
        self.assertEqual(self.status_user()["user"]["id"], ordinary["id"])

        self.assertEqual(self.login(admin, admin=True).status_code, 200)
        self.assertEqual(self.login(ordinary, admin=True).status_code, 403)
        self.assertEqual(self.status_user()["user"]["id"], admin["id"])
        self.assertEqual(self.status_user()["user"]["role"], "admin")

    def test_registration_cannot_grant_roles_and_approved_user_cannot_manage(self):
        username = f"forged-role-{uuid.uuid4().hex[:12]}"
        response = self.client.post("/api/auth/register", json={
            "username": username, "password": self.password,
            "is_admin": True, "role": "admin", "is_approved": True,
        })
        self.assertEqual(response.status_code, 200)
        user = response.get_json()["user"]
        self.created_ids.append(user["id"])
        self.assertFalse(user["is_admin"])
        self.assertFalse(user["is_approved"])
        self.assertEqual(user["role"], "user")
        with app_module.app.app_context():
            db.session.get(User, user["id"]).is_approved = True
            db.session.commit()
        for method, path, payload in (
            ("GET", "/api/admin/profile", None),
            ("POST", "/api/admin/profile", {"current_password": self.password, "is_admin": True}),
            ("GET", "/api/admin/all-users", None),
            ("GET", "/api/admin/metrics", None),
            ("POST", "/api/admin/test-users", {"username": "another-test", "password": self.password}),
        ):
            with self.subTest(path=path, method=method):
                rejected = self.client.open(path, method=method, json=payload)
                self.assertEqual(rejected.status_code, 403)
        with app_module.app.app_context():
            self.assertFalse(db.session.get(User, user["id"]).is_admin)

    def test_admin_profile_edits_only_current_admin_and_new_credentials_work(self):
        admin = self.make_user(is_admin=True)
        ordinary = self.make_user(is_admin=False, is_approved=True)
        self.assertEqual(self.login(admin, admin=True).status_code, 200)
        profile = self.client.get("/api/admin/profile").get_json()["user"]
        self.assertEqual(profile["id"], admin["id"])
        new_username = f"changed-admin-{uuid.uuid4().hex[:12]}"
        new_password = "Changed-admin-password-123"
        updated = self.client.post("/api/admin/profile", json={
            "current_password": self.password, "username": new_username,
            "password": new_password, "user_id": ordinary["id"],
        })
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["user"]["id"], admin["id"])
        self.assertEqual(updated.get_json()["user"]["username"], new_username)
        with app_module.app.app_context():
            untouched = db.session.get(User, ordinary["id"])
            self.assertEqual(untouched.username, ordinary["username"])
            self.assertTrue(check_password_hash(untouched.password_hash, self.password))
            self.assertFalse(untouched.is_admin)
            self.assertTrue(db.session.get(User, admin["id"]).is_admin)
        self.client.post("/api/auth/logout")
        self.assertEqual(self.login(admin, admin=True).status_code, 401)
        changed = {"id": admin["id"], "username": new_username}
        self.assertEqual(self.login(changed, admin=True, password=new_password).status_code, 200)
        self.assertEqual(self.login(changed, password=new_password).status_code, 403)
        self.assertEqual(self.status_user()["user"]["id"], admin["id"])

    def test_admin_profile_accepts_short_password(self):
        admin = self.make_user(is_admin=True)
        self.assertEqual(self.login(admin, admin=True).status_code, 200)
        updated = self.client.post("/api/admin/profile", json={
            "current_password": self.password, "password": "ab",
        })
        self.assertEqual(updated.status_code, 200)
        self.client.post("/api/auth/logout")
        self.assertEqual(self.login(admin, admin=True, password="ab").status_code, 200)

    def test_admin_profile_validation_is_atomic_and_roles_cannot_change(self):
        admin = self.make_user(is_admin=True)
        ordinary = self.make_user(is_admin=False)
        self.login(admin, admin=True)
        for payload, expected in (
            ({"username": "should-not-change"}, 400),
            ({"current_password": "wrong-password", "username": "should-not-change"}, 401),
            ({"current_password": self.password, "username": ordinary["username"]}, 409),
            ({"current_password": self.password, "username": "ab"}, 400),
            ({"current_password": self.password, "password": ["invalid-type"]}, 400),
            ({"current_password": self.password, "is_admin": False}, 400),
            ({"current_password": self.password, "role": "user"}, 400),
            ({"current_password": self.password, "is_approved": False}, 400),
        ):
            with self.subTest(payload=payload):
                response = self.client.post("/api/admin/profile", json=payload)
                self.assertEqual(response.status_code, expected)
                with app_module.app.app_context():
                    row = db.session.get(User, admin["id"])
                    self.assertEqual(row.username, admin["username"])
                    self.assertTrue(check_password_hash(row.password_hash, self.password))
                    self.assertTrue(row.is_admin)
        self.assertEqual(self.client.post("/api/admin/profile", json={
            "current_password": self.password, "username": admin["username"], "password": "",
        }).status_code, 200)

    def test_admin_accounts_are_protected_from_user_management_mutations(self):
        admin = self.make_user(is_admin=True, approval_requested=True, is_approved=False, llm_model="original-model")
        self.login(admin, admin=True)
        for operation in ("approve", "reject", "set-model", "revoke", "delete-user"):
            with self.subTest(operation=operation):
                response = self.client.post(f"/api/admin/{operation}/{admin['id']}", json={"llm_model": "changed-model"})
                self.assertEqual(response.status_code, 400)
        with app_module.app.app_context():
            row = db.session.get(User, admin["id"])
            self.assertTrue(row.is_admin)
            self.assertFalse(row.is_approved)
            self.assertTrue(row.approval_requested)
            self.assertEqual(row.llm_model, "original-model")

    def test_user_listing_groups_roles_and_returns_unlimited_without_keys(self):
        admin = self.make_user(is_admin=True, free_api_used=99)
        approved = self.make_user(is_admin=False, is_approved=True, free_api_used=99)
        personal = self.make_user(is_admin=False, llm_api_key="sk-placeholder-private-user-key", free_api_used=99)
        trial = self.make_user(is_admin=False, free_api_used=3)
        exhausted = self.make_user(is_admin=False, free_api_used=99)
        self.login(admin, admin=True)
        result = self.client.get("/api/admin/all-users").get_json()
        users = {user["id"]: user for user in result["users"]}
        administrators = {user["id"]: user for user in result["administrators"]}
        self.assertNotIn(admin["id"], users)
        self.assertIn(admin["id"], administrators)
        self.assertTrue(all(user["role"] == "user" and not user["is_admin"] for user in users.values()))
        self.assertTrue(all(user["role"] == "admin" and user["is_admin"] for user in administrators.values()))
        for info in (administrators[admin["id"]], users[approved["id"]], users[personal["id"]]):
            self.assertIs(info["ai_unlimited"], True)
            self.assertEqual(info["quota_mode"], "unlimited")
            self.assertIsNone(info["free_api_remaining"])
            self.assertEqual(info["free_api_limit"], 10)
            self.assertNotIn("llm_api_key", info)
            self.assertNotIn("password_hash", info)
        self.assertNotIn("sk-placeholder-private-user-key", str(result))
        self.assertIs(users[trial["id"]]["ai_unlimited"], False)
        self.assertEqual(users[trial["id"]]["quota_mode"], "trial")
        self.assertEqual(users[trial["id"]]["free_api_remaining"], 7)
        self.assertEqual(users[exhausted["id"]]["free_api_remaining"], 0)
        metrics = self.client.get("/api/admin/metrics").get_json()["users"]
        with app_module.app.app_context():
            self.assertEqual(metrics["total"], User.query.filter_by(is_admin=False).count())
            self.assertEqual(metrics["administrator_count"], User.query.filter_by(is_admin=True).count())

    def test_admin_creates_new_approved_test_account_without_reusing_any_account(self):
        admin = self.make_user(is_admin=True)
        ordinary = self.make_user(is_admin=False, is_approved=False)
        self.login(admin, admin=True)
        for existing in (admin, ordinary):
            conflict = self.client.post("/api/admin/test-users", json={
                "username": existing["username"], "password": self.password,
            })
            self.assertEqual(conflict.status_code, 409)
        for payload in (
            {"username": "ab", "password": self.password},
            {"username": "valid-test-user", "password": ""},
            {"username": ["wrong-type"], "password": self.password},
        ):
            self.assertEqual(self.client.post("/api/admin/test-users", json=payload).status_code, 400)
        username = f"new-test-account-{uuid.uuid4().hex[:12]}"
        response = self.client.post("/api/admin/test-users", json={
            "username": username, "password": self.password, "is_admin": True,
            "role": "admin", "is_approved": False, "free_api_used": 999,
        })
        self.assertEqual(response.status_code, 201)
        test_user = response.get_json()["user"]
        self.created_ids.append(test_user["id"])
        self.assertFalse(test_user["is_admin"])
        self.assertTrue(test_user["is_approved"])
        self.assertIs(test_user["ai_unlimited"], True)
        self.assertEqual(test_user["free_api_used"], 0)
        self.assertIsNone(test_user["free_api_remaining"])
        self.assertEqual(self.status_user()["user"]["id"], admin["id"])
        test_client = app_module.app.test_client()
        self.assertEqual(self.login(test_user, client=test_client).status_code, 200)
        self.assertEqual(test_client.get("/api/admin/profile").status_code, 403)
        self.assertEqual(self.login(test_user, admin=True, client=test_client).status_code, 403)
        with app_module.app.app_context():
            self.assertFalse(db.session.get(User, ordinary["id"]).is_approved)
            self.assertTrue(db.session.get(User, admin["id"]).is_admin)


if __name__ == "__main__":
    unittest.main()
