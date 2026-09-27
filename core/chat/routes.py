from datetime import datetime

from flask import Blueprint, jsonify, request, send_file
from flask_login import current_user, login_required

from core.extensions import limiter, socketio
from core.models import User, db
from core.notifications.services import enqueue_notification

from .models import ChatAttachment, ChatAuditLog, ChatMessage, ChatMessageHidden, ChatParticipant, ChatReport, ChatThread, ChatUserSanction, UserBlock
from .services import (
    create_message,
    edit_message,
    ensure_direct_thread,
    mark_read,
    hide_message,
    other_participant,
    participant_for,
    serialize_message,
    serialize_thread,
    recall_message,
)
from .storage import LocalAttachmentStorage


chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@chat_bp.get("/users")
@login_required
@limiter.limit("30 per minute")
def search_users():
    query = request.args.get("q", "").strip()[:80]
    rows = User.query.filter(User.id != current_user.id)
    if query:
        rows = rows.filter(User.username.ilike(f"%{query}%"))
    rows = rows.order_by(User.username.asc()).limit(20).all()
    blocked_ids = {row.blocked_id for row in UserBlock.query.filter_by(blocker_id=current_user.id).all()}
    return jsonify({"users": [
        {"id": row.id, "username": row.username, "blocked": row.id in blocked_ids}
        for row in rows if row.id not in blocked_ids
    ]})


@chat_bp.get("/threads")
@login_required
def list_threads():
    rows = ChatThread.query.join(ChatParticipant, ChatParticipant.thread_id == ChatThread.id).filter(
        ChatParticipant.user_id == current_user.id
    ).order_by(ChatThread.updated_at.desc()).all()
    return jsonify({"threads": [serialize_thread(row, current_user.id) for row in rows]})


@chat_bp.post("/threads")
@login_required
@limiter.limit("20 per hour")
def create_thread():
    data = request.get_json(silent=True) or {}
    try:
        thread = ensure_direct_thread(current_user.id, int(data.get("user_id")))
    except (TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"status": "ok", "thread": serialize_thread(thread, current_user.id)}), 201


@chat_bp.get("/threads/<thread_id>/messages")
@login_required
@limiter.limit("90 per minute")
def messages(thread_id):
    if participant_for(thread_id, current_user.id) is None:
        return jsonify({"error": "会话不存在或无权访问"}), 404
    limit = max(1, min(request.args.get("limit", 60, type=int), 100))
    query = ChatMessage.query.filter_by(thread_id=thread_id).filter(~ChatMessage.id.in_(
        db.session.query(ChatMessageHidden.message_id).filter(ChatMessageHidden.user_id == current_user.id)
    ))
    before = request.args.get("before_sequence", type=int)
    after = request.args.get("after_sequence", type=int)
    if before is not None:
        query = query.filter(ChatMessage.sequence < before)
    if after is not None:
        query = query.filter(ChatMessage.sequence > after)
    rows = query.order_by(ChatMessage.sequence.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    rows.reverse()
    delivered = False
    for row in rows:
        if row.sender_id != current_user.id and row.status == "sent":
            row.status, row.delivered_at, delivered = "delivered", datetime.utcnow(), True
    if delivered:
        db.session.commit()
    return jsonify({"messages": [serialize_message(row) for row in rows], "has_more": has_more})


@chat_bp.post("/threads/<thread_id>/messages")
@login_required
@limiter.limit("120 per minute")
def send_message_fallback(thread_id):
    data = request.get_json(silent=True) or {}
    try:
        message = create_message(
            thread_id, current_user.id, data.get("body"),
            client_message_id=data.get("client_message_id"), reply_to_id=data.get("reply_to_id"),
            message_type=data.get("message_type", "text"),
        )
    except PermissionError as error:
        return jsonify({"error": str(error)}), 403
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    payload = serialize_message(message)
    if getattr(message, "_idempotent_replay", False):
        return jsonify({"status": "ok", "message": payload, "idempotent_replay": True}), 200
    socketio.emit("chat_message", payload, to=f"chat:{thread_id}", namespace="/chat")
    recipient = other_participant(thread_id, current_user.id)
    if recipient:
        socketio.emit("chat_message", payload, to=f"user:{recipient.user_id}", namespace="/chat")
        enqueue_notification(
            recipient.user_id, "chat_message", "收到一条新私信", "打开明鉴查看消息",
            route=f"/chat?thread={thread_id}", idempotency_key=f"chat:{message.id}",
        )
    return jsonify({"status": "ok", "message": payload}), 201


@chat_bp.post("/threads/<thread_id>/attachments")
@login_required
@limiter.limit("30 per hour")
def send_attachment(thread_id):
    if participant_for(thread_id, current_user.id) is None:
        return jsonify({"error": "会话不存在或无权访问"}), 404
    upload = request.files.get("file")
    if upload is None:
        return jsonify({"error": "请选择附件"}), 400
    client_message_id = str(request.form.get("client_message_id", "")).strip()[:64]
    if client_message_id:
        existing = ChatMessage.query.filter_by(sender_id=current_user.id, client_message_id=client_message_id, thread_id=thread_id).first()
        if existing:
            return jsonify({"status": "ok", "message": serialize_message(existing), "idempotent_replay": True}), 200
    storage, saved = LocalAttachmentStorage(), None
    try:
        saved = storage.save(upload)
        message_type = "image" if saved["mime_type"].startswith("image/") else "attachment"
        message = create_message(
            thread_id, current_user.id, request.form.get("body", ""),
            client_message_id=client_message_id,
            reply_to_id=request.form.get("reply_to_id"), message_type=message_type, attachment=saved,
        )
        if getattr(message, "_idempotent_replay", False):
            storage.delete(saved["storage_key"])
    except PermissionError as error:
        if saved:
            storage.delete(saved["storage_key"])
        return jsonify({"error": str(error)}), 403
    except ValueError as error:
        if saved:
            storage.delete(saved["storage_key"])
        return jsonify({"error": str(error)}), 400
    payload = serialize_message(message)
    socketio.emit("chat_message", payload, to=f"chat:{thread_id}", namespace="/chat")
    recipient = other_participant(thread_id, current_user.id)
    if recipient:
        enqueue_notification(recipient.user_id, "chat_message", "收到一个新附件", "打开明鉴查看详情", route=f"/chat?thread={thread_id}", idempotency_key=f"chat:{message.id}")
    return jsonify({"status": "ok", "message": payload}), 201


@chat_bp.get("/attachments/<attachment_id>")
@login_required
def download_attachment(attachment_id):
    row = ChatAttachment.query.get(str(attachment_id))
    message = ChatMessage.query.get(row.message_id) if row else None
    if row is None or message is None or participant_for(message.thread_id, current_user.id) is None:
        return jsonify({"error": "附件不存在或无权访问"}), 404
    try:
        response = send_file(LocalAttachmentStorage().path_for(row.storage_key), mimetype=row.mime_type, as_attachment=True, download_name=row.original_name)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response
    except FileNotFoundError:
        return jsonify({"error": "附件文件不存在"}), 404


@chat_bp.put("/messages/<message_id>")
@login_required
def update_message(message_id):
    try:
        message = edit_message(message_id, current_user.id, (request.get_json(silent=True) or {}).get("body"))
    except PermissionError as error:
        return jsonify({"error": str(error)}), 403
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    payload = serialize_message(message)
    socketio.emit("chat_message_updated", payload, to=f"chat:{message.thread_id}", namespace="/chat")
    return jsonify({"status": "ok", "message": payload})


@chat_bp.post("/messages/<message_id>/recall")
@login_required
def recall(message_id):
    try:
        message = recall_message(message_id, current_user.id)
    except PermissionError as error:
        return jsonify({"error": str(error)}), 403
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    payload = serialize_message(message)
    socketio.emit("chat_message_updated", payload, to=f"chat:{message.thread_id}", namespace="/chat")
    return jsonify({"status": "ok", "message": payload})


@chat_bp.delete("/messages/<message_id>")
@login_required
def delete_message_for_me(message_id):
    try:
        hide_message(message_id, current_user.id)
    except PermissionError as error:
        return jsonify({"error": str(error)}), 403
    return jsonify({"status": "ok"})


@chat_bp.post("/messages/<message_id>/report")
@login_required
@limiter.limit("20 per hour")
def report_message(message_id):
    message = ChatMessage.query.get(str(message_id))
    if message is None or participant_for(message.thread_id, current_user.id) is None:
        return jsonify({"error": "消息不存在或无权访问"}), 404
    reason = str((request.get_json(silent=True) or {}).get("reason", "")).strip()[:240]
    if not reason:
        return jsonify({"error": "请填写举报原因"}), 400
    db.session.add(ChatReport(message_id=message.id, reporter_id=current_user.id, reason=reason))
    db.session.commit()
    return jsonify({"status": "ok"}), 201


@chat_bp.get("/threads/<thread_id>/search")
@login_required
@limiter.limit("30 per minute")
def search_messages(thread_id):
    if participant_for(thread_id, current_user.id) is None:
        return jsonify({"error": "会话不存在或无权访问"}), 404
    query = request.args.get("q", "").strip()[:80]
    if not query:
        return jsonify({"messages": []})
    rows = ChatMessage.query.filter(
        ChatMessage.thread_id == thread_id, ChatMessage.status.in_(("sent", "delivered")),
        ChatMessage.body.ilike(f"%{query.replace('%', '')}%"),
    ).order_by(ChatMessage.sequence.desc()).limit(50).all()
    return jsonify({"messages": [serialize_message(row) for row in rows]})


@chat_bp.post("/threads/<thread_id>/read")
@login_required
def read_thread(thread_id):
    data = request.get_json(silent=True) or {}
    try:
        message = mark_read(thread_id, current_user.id, data.get("message_id"))
    except PermissionError as error:
        return jsonify({"error": str(error)}), 403
    socketio.emit("chat_read", {"thread_id": thread_id, "user_id": current_user.id, "message_id": message.id if message else None}, to=f"chat:{thread_id}", namespace="/chat")
    return jsonify({"status": "ok"})


@chat_bp.post("/blocks/<int:user_id>")
@login_required
def toggle_block(user_id):
    if user_id == current_user.id or User.query.get(user_id) is None:
        return jsonify({"error": "用户不存在"}), 404
    row = UserBlock.query.filter_by(blocker_id=current_user.id, blocked_id=user_id).first()
    blocked = row is None
    if blocked:
        db.session.add(UserBlock(blocker_id=current_user.id, blocked_id=user_id))
    else:
        db.session.delete(row)
    db.session.commit()
    return jsonify({"status": "ok", "blocked": blocked})


def _admin_only():
    return bool(current_user.is_authenticated and current_user.is_admin)


@chat_bp.get("/admin/reports")
@login_required
def admin_reports():
    if not _admin_only():
        return jsonify({"error": "需要管理员权限"}), 403
    rows = ChatReport.query.order_by(ChatReport.created_at.desc()).limit(200).all()
    return jsonify({"reports": [{"id": row.id, "message_id": row.message_id, "reporter_id": row.reporter_id, "reason": row.reason, "status": row.status, "created_at": row.created_at.isoformat()} for row in rows]})


@chat_bp.post("/admin/messages/<message_id>/moderate")
@login_required
def moderate_message(message_id):
    if not _admin_only():
        return jsonify({"error": "需要管理员权限"}), 403
    message = ChatMessage.query.get(str(message_id))
    if message is None:
        return jsonify({"error": "消息不存在"}), 404
    reason = str((request.get_json(silent=True) or {}).get("reason", "违反社区规则")).strip()[:240]
    message.status, message.moderation_reason, message.body = "moderated", reason, ""
    db.session.add(ChatAuditLog(actor_id=current_user.id, action="moderate_message", target_type="message", target_id=message.id, metadata_json="{}"))
    ChatReport.query.filter_by(message_id=message.id, status="pending").update({"status": "resolved"}, synchronize_session=False)
    db.session.commit()
    payload = serialize_message(message)
    socketio.emit("chat_message_updated", payload, to=f"chat:{message.thread_id}", namespace="/chat")
    return jsonify({"status": "ok", "message": payload})


@chat_bp.put("/admin/users/<int:user_id>/sanction")
@login_required
def sanction_user(user_id):
    if not _admin_only():
        return jsonify({"error": "需要管理员权限"}), 403
    data = request.get_json(silent=True) or {}
    action = str(data.get("action", ""))
    row = ChatUserSanction.query.get(user_id) or ChatUserSanction(user_id=user_id)
    if action == "ban":
        row.banned_at = datetime.utcnow()
    elif action == "mute":
        minutes = max(1, min(int(data.get("minutes", 60)), 43200))
        from datetime import timedelta
        row.muted_until = datetime.utcnow() + timedelta(minutes=minutes)
    elif action == "clear":
        row.banned_at = row.muted_until = None
    else:
        return jsonify({"error": "action 必须是 ban、mute 或 clear"}), 400
    row.reason, row.moderator_id = str(data.get("reason", ""))[:240], current_user.id
    db.session.add(row)
    db.session.add(ChatAuditLog(actor_id=current_user.id, action=f"sanction_{action}", target_type="user", target_id=str(user_id)))
    db.session.commit()
    return jsonify({"status": "ok", "action": action})
