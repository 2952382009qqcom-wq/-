"""管理员操作日志：谁、什么时候、干了什么、IP。"""

from flask import request

from core.models import db

from .models import AdminActionLog


def client_ip():
    try:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
        return (request.remote_addr or "")[:64]
    except RuntimeError:
        return ""


def log_admin_action(action, *, target_type="", target_id="", detail="", actor=None):
    """记录一条管理操作日志（不提交事务，由调用方统一 commit）。"""
    if actor is None:
        from flask_login import current_user

        actor = current_user if getattr(current_user, "is_authenticated", False) else None
    log = AdminActionLog(
        actor_id=getattr(actor, "id", None),
        actor_username=(getattr(actor, "username", "") or "")[:80],
        action=str(action)[:48],
        target_type=str(target_type)[:32],
        target_id=str(target_id)[:64],
        detail=str(detail)[:500],
        ip=client_ip(),
    )
    db.session.add(log)
    return log
