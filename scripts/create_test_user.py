"""Explicit operator command: create one ordinary, approved competition user."""
import argparse
import getpass
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    username = args.username.strip()
    if not 3 <= len(username) <= 80:
        parser.error("username must be 3..80 characters")
    if not os.getenv("DATABASE_URL"):
        parser.error("DATABASE_URL must be explicitly configured; no default database is chosen")
    password = getpass.getpass("Test account password (12+ characters): ")
    if len(password) < 12 or password != getpass.getpass("Confirm test password: "):
        parser.error("password is too short or confirmation differs")
    os.environ["AUTO_INIT_DB"] = "0"
    os.environ["AUTO_SEED_REFERENCE_DATA"] = "0"
    import app as application
    from core.models import User, db
    from werkzeug.security import generate_password_hash
    with application.app.app_context():
        if User.query.filter_by(username=username).first():
            parser.error("username already exists; no account was changed")
        user = User(username=username, password_hash=generate_password_hash(password),
                    is_admin=False, is_approved=True, free_api_used=0)
        db.session.add(user)
        db.session.commit()
        print(f"Created ordinary approved test account: {username}")
        print("Application usage is unlimited; provider billing and rate limits still apply.")


if __name__ == "__main__":
    main()
