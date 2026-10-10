"""Isolated local preview. Never inherits a production database or service URL."""
from __future__ import annotations

import argparse
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def configure_local_environment(port=5090):
    from dotenv import dotenv_values, set_key

    settings_file = ROOT / ".env.local"
    values = dotenv_values(settings_file) if settings_file.exists() else {}
    defaults = {
        "SECRET_KEY": secrets.token_urlsafe(48),
        "MINGJIAN_LOCAL_ADMIN_USERNAME": "mingjian_admin",
        "MINGJIAN_LOCAL_ADMIN_PASSWORD": secrets.token_urlsafe(18),
        "MINGJIAN_LOCAL_TEST_USERNAME": "mingjian_test",
        "MINGJIAN_LOCAL_TEST_PASSWORD": secrets.token_urlsafe(18),
        "LLM_API_KEY": "",
        "LLM_BASE_URL": "https://api.deepseek.com/v1",
        "LLM_MODEL": "deepseek-flash",
    }
    for key, default in defaults.items():
        if key not in values or values[key] is None:
            set_key(str(settings_file), key, default, quote_mode="always")
            values[key] = default
    for key, value in values.items():
        if value is not None:
            os.environ[key] = value
    for key in ("MINGJIAN_LOCAL_ADMIN_USERNAME", "MINGJIAN_LOCAL_TEST_USERNAME"):
        if not 3 <= len(values[key]) <= 80 or values[key] != values[key].strip():
            raise RuntimeError(f"{key} must be 3..80 characters without surrounding whitespace")
    for key in ("MINGJIAN_LOCAL_ADMIN_PASSWORD", "MINGJIAN_LOCAL_TEST_PASSWORD"):
        if len(values[key]) < 12:
            raise RuntimeError(f"{key} must contain at least 12 characters")
    os.chmod(settings_file, 0o600)
    instance = ROOT / "instance"
    instance.mkdir(exist_ok=True)
    # Force local persistence and disabled external helpers even if a parent
    # shell or accidentally copied .env contains real deployment values.
    os.environ.update({
        "DATABASE_URL": "sqlite:///" + (instance / "local-demo.db").as_posix(),
        "AUTO_INIT_DB": "1",
        "AUTO_SEED_REFERENCE_DATA": "1",
        "RATELIMIT_STORAGE_URI": "memory://",
        "SOCKETIO_REDIS_URL": "",
        "MEILISEARCH_URL": "",
        "MEILISEARCH_API_KEY": "",
        "CELERY_BROKER_URL": "memory://",
        "CELERY_RESULT_BACKEND": "cache+memory://",
        "FCM_ENDPOINT": "",
        "FCM_BEARER_TOKEN": "",
        "CHAT_ATTACHMENT_ROOT": str(instance / "chat-attachments"),
        "RECOMMENDER_ARTIFACT": str(instance / "models" / "local-recommender.json"),
        "CORS_ORIGINS": f"http://127.0.0.1:{port},http://localhost:{port}",
        "COOKIE_SECURE": "0",
        "APP_VERSION": "2026.10-account-isolation-local",
    })
    os.chdir(ROOT)
    return settings_file, values


def provision_local_accounts(values, account_file=None, port=5090):
    import app as application
    from core.models import User, db
    from werkzeug.security import generate_password_hash

    with application.app.app_context():
        database = str(db.engine.url.database or "")
        if db.engine.url.get_backend_name() != "sqlite" or Path(database).resolve() != (ROOT / "instance" / "local-demo.db").resolve():
            raise RuntimeError("Local preview refused a non-local database")
        admin = User.query.filter_by(is_admin=True).first()
        admin_name = values["MINGJIAN_LOCAL_ADMIN_USERNAME"]
        test_name = values["MINGJIAN_LOCAL_TEST_USERNAME"]
        if admin_name == test_name:
            raise RuntimeError("Administrator and test usernames must differ")
        if admin is None:
            if User.query.filter_by(username=admin_name).first():
                raise RuntimeError("An ordinary account already owns the admin username; no promotion performed")
            admin = User(username=admin_name,
                         password_hash=generate_password_hash(values["MINGJIAN_LOCAL_ADMIN_PASSWORD"]),
                         is_admin=True, is_approved=True)
            db.session.add(admin)
        test_user = User.query.filter_by(username=test_name).first()
        if test_user and test_user.is_admin:
            raise RuntimeError("The test username belongs to an administrator; no change performed")
        if test_user is None:
            test_user = User(username=test_name,
                             password_hash=generate_password_hash(values["MINGJIAN_LOCAL_TEST_PASSWORD"]),
                             is_admin=False, is_approved=True, free_api_used=0)
            db.session.add(test_user)
        # Existing passwords, renamed administrators and approval decisions are
        # deliberately unchanged on subsequent starts.
        db.session.commit()
        details_file = account_file or ROOT.parent / "本地账号资料_勿上传.txt"
        if not details_file.exists():
            with details_file.open("x", encoding="utf-8") as output:
                output.write(
                    "明鉴本地预览初始账号资料（不要上传 GitHub 或参赛源码）\n\n"
                    f"管理员入口：http://127.0.0.1:{port}/admin\n管理员账号：{admin.username}\n"
                    f"管理员初始密码：{values['MINGJIAN_LOCAL_ADMIN_PASSWORD']}\n\n"
                    f"测试入口：http://127.0.0.1:{port}/\n测试账号：{test_user.username}\n"
                    f"测试初始密码：{values['MINGJIAN_LOCAL_TEST_PASSWORD']}\n\n"
                    "测试账号是普通已批准用户：应用内不限次数，不拥有管理员权限。\n"
                    "上游 API 仍按实际使用计费、受余额和速率限制。\n"
                    "密钥未从服务器取得，当前尚未接通真实 DeepSeek 服务。\n"
                    "在管理页修改密码后以新密码为准；重启不会恢复初始密码。\n"
                )
            os.chmod(details_file, 0o600)
    return application, details_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup-only", action="store_true")
    parser.add_argument("--port", type=int, default=5090)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be in the range 1024..65535")
    settings_file, values = configure_local_environment(args.port)
    application, details_file = provision_local_accounts(values, port=args.port)
    application.app.config["MODEL_CONFIG_ENV_PATH"] = str(settings_file)
    print(f"Local accounts ready. Credentials are in: {details_file}")
    print("No production server or database was modified.")
    if not args.setup_only:
        print(f"User page: http://127.0.0.1:{args.port}/")
        print(f"Admin page: http://127.0.0.1:{args.port}/admin")
        application.socketio.run(application.app, host="127.0.0.1", port=args.port,
                                 debug=False, use_reloader=False, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
