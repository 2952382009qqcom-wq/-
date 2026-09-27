import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


def token_hash(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def _fernet():
    secret = str(current_app.config["SECRET_KEY"]).encode("utf-8")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret).digest()))


def encrypt_token(token):
    return _fernet().encrypt(str(token).encode("utf-8")).decode("ascii")


def decrypt_token(value):
    try:
        return _fernet().decrypt(str(value).encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        raise ValueError("推送令牌无法解密") from None
