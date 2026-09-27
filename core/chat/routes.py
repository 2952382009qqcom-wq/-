from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from core.extensions import limiter, socketio
from core.models import User, db

from .models import ChatMessage, ChatParticipant, ChatThread, UserBlock
from .services import (
    create_message,
    ensure_direct_thread,
    mark_read,
    other_participant,
    participant_for,
    serialize_message,
    serialize_thread,
)


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
    rows = ChatMessage.query.filter_by(thread_id=thread_id).order_by(ChatMessage.created_at.desc()).limit(limit).all()
    rows.reverse()
    return jsonify({"messages": [serialize_message(row) for row in rows]})


@chat_bp.post("/threads/<thread_id>/messages")
@login_required
@limiter.limit("120 per minute")
def send_message_fallback(thread_id):
    data = request.get_json(silent=True) or {}
    try:
        message = create_message(thread_id, current_user.id, data.get("body"))
    except PermissionError as error:
        return jsonify({"error": str(error)}), 403
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    payload = serialize_message(message)
    socketio.emit("chat_message", payload, to=f"chat:{thread_id}", namespace="/chat")
    recipient = other_participant(thread_id, current_user.id)
    if recipient:
        socketio.emit("chat_message", payload, to=f"user:{recipient.user_id}", namespace="/chat")
    return jsonify({"status": "ok", "message": payload}), 201


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
