"""Attachment storage abstraction with an isolated local implementation."""

import hashlib
import mimetypes
import os
import secrets
from pathlib import Path

from werkzeug.utils import secure_filename


ALLOWED_MIMES = {
    "image/jpeg": {".jpg", ".jpeg"}, "image/png": {".png"}, "image/gif": {".gif"},
    "application/pdf": {".pdf"}, "text/plain": {".txt"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
}


def _matches_signature(mime, data):
    signatures = {
        "image/jpeg": (b"\xff\xd8\xff",), "image/png": (b"\x89PNG\r\n\x1a\n",),
        "image/gif": (b"GIF87a", b"GIF89a"), "application/pdf": (b"%PDF-",),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (b"PK\x03\x04",),
    }
    if mime == "text/plain":
        try:
            data.decode("utf-8")
            return b"\x00" not in data
        except UnicodeDecodeError:
            return False
    return any(data.startswith(prefix) for prefix in signatures.get(mime, ()))


class LocalAttachmentStorage:
    def __init__(self, root=None, max_bytes=None):
        self.root = Path(root or os.getenv("CHAT_ATTACHMENT_ROOT", "instance/chat-attachments")).resolve()
        self.max_bytes = int(max_bytes or os.getenv("CHAT_ATTACHMENT_MAX_BYTES", 10 * 1024 * 1024))

    def save(self, upload):
        original = secure_filename(upload.filename or "")
        suffix = Path(original).suffix.lower()
        mime = str(upload.mimetype or mimetypes.guess_type(original)[0] or "")
        if mime not in ALLOWED_MIMES or suffix not in ALLOWED_MIMES[mime]:
            raise ValueError("不支持的附件类型")
        data = upload.read(self.max_bytes + 1)
        if not data or len(data) > self.max_bytes:
            raise ValueError("附件为空或超过大小限制")
        if not _matches_signature(mime, data):
            raise ValueError("附件内容与声明类型不一致")
        key = f"{secrets.token_hex(16)}{suffix}"
        self.root.mkdir(parents=True, exist_ok=True)
        target = (self.root / key).resolve()
        if target.parent != self.root:
            raise ValueError("附件路径无效")
        target.write_bytes(data)
        return {"storage_key": key, "original_name": original[:255], "mime_type": mime, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def path_for(self, key):
        target = (self.root / str(key)).resolve()
        if target.parent != self.root or not target.is_file():
            raise FileNotFoundError(key)
        return target

    def delete(self, key):
        try:
            self.path_for(key).unlink()
        except FileNotFoundError:
            pass
