from flask_login import current_user
from flask_socketio import disconnect, emit, join_room, leave_room

from core.extensions import socketio

from .services import create_message, mark_read, other_participant, participant_for, serialize_message


@socketio.on("connect", namespace="/chat")
def chat_connect(auth=None):
    if not current_user.is_authenticated:
        return False
    join_room(f"user:{current_user.id}")
    emit("chat_ready", {"user_id": current_user.id})


@socketio.on("join_thread", namespace="/chat")
def chat_join(data):
    thread_id = str((data or {}).get("thread_id") or "")
    if not thread_id or participant_for(thread_id, current_user.id) is None:
        emit("chat_error", {"error": "会话不存在或无权访问"})
        return
    join_room(f"chat:{thread_id}")
    emit("thread_joined", {"thread_id": thread_id})


@socketio.on("leave_thread", namespace="/chat")
def chat_leave(data):
    thread_id = str((data or {}).get("thread_id") or "")
    if thread_id:
        leave_room(f"chat:{thread_id}")


@socketio.on("send_message", namespace="/chat")
def chat_send(data):
    thread_id = str((data or {}).get("thread_id") or "")
    try:
        message = create_message(thread_id, current_user.id, (data or {}).get("body"))
    except (PermissionError, ValueError) as error:
        emit("chat_error", {"error": str(error)})
        return
    payload = serialize_message(message)
    emit("chat_message", payload, to=f"chat:{thread_id}")
    recipient = other_participant(thread_id, current_user.id)
    if recipient:
        emit("chat_message", payload, to=f"user:{recipient.user_id}")


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
