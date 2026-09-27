from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from core.models import db
from core.taxonomy import infer_legal_domain

from .models import UserMemoryAudit, UserMemoryEmbedding, UserMemoryItem
from .services import create_memory, memory_enabled, sanitize_memory_content, set_memory_enabled


memory_bp = Blueprint("memory", __name__, url_prefix="/api/memory")


def _serialize(row):
    return {"id": row.id, "memory_type": row.memory_type, "legal_domain": row.legal_domain, "content": row.content, "confidence": row.confidence, "reason": row.reason, "source_conversation_id": row.source_conversation_id, "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None, "created_at": row.created_at.isoformat()}


@memory_bp.route("/settings", methods=["GET", "PUT"])
@login_required
def settings():
    if request.method == "PUT":
        enabled = (request.get_json(silent=True) or {}).get("enabled")
        if not isinstance(enabled, bool):
            return jsonify({"error": "enabled 必须是布尔值"}), 400
        set_memory_enabled(current_user.id, enabled)
    return jsonify({"enabled": memory_enabled(current_user.id)})


@memory_bp.route("/items", methods=["GET", "POST", "DELETE"])
@login_required
def items():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        try:
            row = create_memory(current_user.id, data.get("content"), data.get("memory_type"), conversation_id=data.get("conversation_id"), message_id=data.get("message_id"), reason=data.get("reason", "用户主动保存"))
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"status": "ok", "item": _serialize(row)}), 201
    rows = UserMemoryItem.query.filter_by(user_id=current_user.id).filter(UserMemoryItem.deleted_at.is_(None)).order_by(UserMemoryItem.created_at.desc()).all()
    if request.method == "DELETE":
        now = datetime.utcnow()
        for row in rows:
            row.deleted_at = now
        db.session.add(UserMemoryAudit(user_id=current_user.id, action="clear", reason="用户清空长期记忆"))
        db.session.commit()
        return jsonify({"status": "ok", "deleted": len(rows)})
    return jsonify({"enabled": memory_enabled(current_user.id), "items": [_serialize(row) for row in rows]})


@memory_bp.route("/items/<memory_id>", methods=["PUT", "DELETE"])
@login_required
def item(memory_id):
    row = UserMemoryItem.query.filter_by(id=memory_id, user_id=current_user.id).filter(UserMemoryItem.deleted_at.is_(None)).first()
    if row is None:
        return jsonify({"error": "记忆不存在"}), 404
    if request.method == "DELETE":
        row.deleted_at = datetime.utcnow()
        action = "delete"
    else:
        try:
            row.content = sanitize_memory_content((request.get_json(silent=True) or {}).get("content"))
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        row.legal_domain = infer_legal_domain(row.content)
        UserMemoryEmbedding.query.filter_by(memory_id=row.id).delete(synchronize_session=False)
        action = "edit"
    db.session.add(UserMemoryAudit(user_id=current_user.id, memory_id=row.id, action=action, reason="用户主动操作"))
    db.session.commit()
    return jsonify({"status": "ok", "item": _serialize(row) if action == "edit" else None})


@memory_bp.get("/export")
@login_required
def export():
    rows = UserMemoryItem.query.filter_by(user_id=current_user.id).order_by(UserMemoryItem.created_at.asc()).all()
    return jsonify({"exported_at": datetime.utcnow().isoformat(), "enabled": memory_enabled(current_user.id), "items": [_serialize(row) for row in rows if row.deleted_at is None]})


@memory_bp.get("/items/<memory_id>/usage")
@login_required
def usage(memory_id):
    row = UserMemoryItem.query.filter_by(id=memory_id, user_id=current_user.id).first()
    if row is None:
        return jsonify({"error": "记忆不存在"}), 404
    audits = UserMemoryAudit.query.filter_by(user_id=current_user.id, memory_id=row.id, action="retrieve").order_by(UserMemoryAudit.created_at.desc()).limit(100).all()
    return jsonify({"memory_id": row.id, "why_saved": row.reason, "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None, "usage": [{"reason": audit.reason, "created_at": audit.created_at.isoformat()} for audit in audits]})
