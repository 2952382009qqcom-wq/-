from flask_login import current_user
from flask_socketio import disconnect, emit, join_room, leave_room

from core.extensions import socketio
from core.notifications.services import enqueue_notification

from core.models import db

from .models import ChatMessage, ChatMessageHidden, ChatParticipant
from .services import create_message, mark_read, other_participant, participant_for, serialize_message


@socketio.on("connect", namespace="/chat")
def chat_connect(auth=None):
    if not current_user.is_authenticated:
        return False
    join_room(f"user:{current_user.id}")
    emit("chat_ready", {"user_id": current_user.id})
    peers = ChatParticipant.query.filter(ChatParticipant.thread_id.in_(
        ChatParticipant.query.with_entities(ChatParticipant.thread_id).filter_by(user_id=current_user.id)
    ), ChatParticipant.user_id != current_user.id).all()
    for peer in peers:
        emit("chat_presence", {"user_id": current_user.id, "online": True}, to=f"user:{peer.user_id}")


@socketio.on("disconnect", namespace="/chat")
def chat_disconnect():
    if not current_user.is_authenticated:
        return
    peers = ChatParticipant.query.filter(ChatParticipant.thread_id.in_(
        ChatParticipant.query.with_entities(ChatParticipant.thread_id).filter_by(user_id=current_user.id)
    ), ChatParticipant.user_id != current_user.id).all()
    for peer in peers:
        emit("chat_presence", {"user_id": current_user.id, "online": False}, to=f"user:{peer.user_id}")


@socketio.on("join_thread", namespace="/chat")
def chat_join(data):
    thread_id = str((data or {}).get("thread_id") or "")
    if not thread_id or participant_for(thread_id, current_user.id) is None:
        emit("chat_error", {"error": "会话不存在或无权访问"})
        return {"ok": False, "error": "forbidden"}
    join_room(f"chat:{thread_id}")
    emit("thread_joined", {"thread_id": thread_id})
    return {"ok": True, "thread_id": thread_id}


@socketio.on("leave_thread", namespace="/chat")
def chat_leave(data):
    thread_id = str((data or {}).get("thread_id") or "")
    if thread_id:
        leave_room(f"chat:{thread_id}")


@socketio.on("send_message", namespace="/chat")
def chat_send(data):
    thread_id = str((data or {}).get("thread_id") or "")
    try:
        message = create_message(
            thread_id, current_user.id, (data or {}).get("body"),
            client_message_id=(data or {}).get("client_message_id"),
            reply_to_id=(data or {}).get("reply_to_id"),
            message_type=(data or {}).get("message_type", "text"),
        )
    except (PermissionError, ValueError) as error:
        emit("chat_error", {"error": str(error)})
        return {"ok": False, "error": str(error)}
    payload = serialize_message(message)
    if getattr(message, "_idempotent_replay", False):
        return {"ok": True, "message": payload, "idempotent_replay": True}
    emit("chat_message", payload, to=f"chat:{thread_id}")
    recipient = other_participant(thread_id, current_user.id)
    if recipient:
        emit("chat_message", payload, to=f"user:{recipient.user_id}")
        enqueue_notification(recipient.user_id, "chat_message", "收到一条新私信", "打开明鉴查看消息", route=f"/?chat=1&thread={thread_id}", idempotency_key=f"chat:{message.id}")
    return {"ok": True, "message": payload}


@socketio.on("sync_messages", namespace="/chat")
def chat_sync(data):
    thread_id = str((data or {}).get("thread_id") or "")
    if participant_for(thread_id, current_user.id) is None:
        return {"ok": False, "error": "forbidden"}
    try:
        after = max(0, int((data or {}).get("after_sequence", 0)))
    except (TypeError, ValueError):
        after = 0
    rows = ChatMessage.query.filter(
        ChatMessage.thread_id == thread_id,
        ChatMessage.sequence > after,
        ~ChatMessage.id.in_(
            db.session.query(ChatMessageHidden.message_id).filter(ChatMessageHidden.user_id == current_user.id)
        ),
    ).order_by(ChatMessage.sequence.asc()).limit(200).all()
    return {"ok": True, "messages": [serialize_message(row) for row in rows], "has_more": len(rows) == 200}


@socketio.on("typing", namespace="/chat")
def chat_typing(data):
    thread_id = str((data or {}).get("thread_id") or "")
    if participant_for(thread_id, current_user.id) is None:
        return
    emit("chat_typing", {"thread_id": thread_id, "user_id": current_user.id, "typing": bool((data or {}).get("typing"))}, to=f"chat:{thread_id}", include_self=False)


@socketio.on("mark_read", namespace="/chat")
def chat_mark_read(data):
    thread_id = str((data or {}).get("thread_id") or "")
    try:
        message = mark_read(thread_id, current_user.id, (data or {}).get("message_id"))
    except PermissionError:
        return
    emit("chat_read", {"thread_id": thread_id, "user_id": current_user.id, "message_id": message.id if message else None}, to=f"chat:{thread_id}")
