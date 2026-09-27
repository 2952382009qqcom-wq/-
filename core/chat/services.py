from datetime import datetime

from sqlalchemy import or_

from core.models import User, db

from .models import ChatMessage, ChatParticipant, ChatThread, UserBlock


def pair_key(left_id, right_id):
    low, high = sorted((int(left_id), int(right_id)))
    return f"{low}:{high}"


def is_blocked(left_id, right_id):
    return bool(UserBlock.query.filter(or_(
        (UserBlock.blocker_id == left_id) & (UserBlock.blocked_id == right_id),
        (UserBlock.blocker_id == right_id) & (UserBlock.blocked_id == left_id),
    )).first())


def ensure_direct_thread(user_id, other_user_id):
    if int(user_id) == int(other_user_id):
        raise ValueError("不能与自己创建私聊")
    other = User.query.get(int(other_user_id))
    if other is None:
        raise ValueError("用户不存在")
    if is_blocked(user_id, other_user_id):
        raise ValueError("当前无法与该用户私聊")
    key = pair_key(user_id, other_user_id)
    thread = ChatThread.query.filter_by(pair_key=key).first()
    if thread is None:
        thread = ChatThread(pair_key=key)
        db.session.add(thread)
        db.session.flush()
        db.session.add(ChatParticipant(thread_id=thread.id, user_id=user_id))
        db.session.add(ChatParticipant(thread_id=thread.id, user_id=other_user_id))
        db.session.commit()
    return thread


def participant_for(thread_id, user_id):
    return ChatParticipant.query.filter_by(thread_id=str(thread_id), user_id=int(user_id)).first()


def other_participant(thread_id, user_id):
    return ChatParticipant.query.filter(
        ChatParticipant.thread_id == str(thread_id), ChatParticipant.user_id != int(user_id)
    ).first()


def serialize_message(message):
    return {
        "id": message.id,
        "thread_id": message.thread_id,
        "sender_id": message.sender_id,
        "sender_name": message.sender.username if message.sender else "已注销用户",
        "body": "消息已撤回" if message.status == "recalled" else message.body,
        "status": message.status,
        "created_at": message.created_at.isoformat(timespec="seconds"),
    }


def serialize_thread(thread, user_id):
    other = other_participant(thread.id, user_id)
    last = ChatMessage.query.filter_by(thread_id=thread.id).order_by(ChatMessage.created_at.desc()).first()
    me = participant_for(thread.id, user_id)
    unread_query = ChatMessage.query.filter(
        ChatMessage.thread_id == thread.id,
        ChatMessage.sender_id != user_id,
        ChatMessage.status == "sent",
    )
    if me and me.last_read_message_id:
        marker = ChatMessage.query.get(me.last_read_message_id)
        if marker:
            unread_query = unread_query.filter(ChatMessage.created_at > marker.created_at)
    return {
        "id": thread.id,
        "other_user": {"id": other.user.id, "username": other.user.username} if other and other.user else None,
        "last_message": serialize_message(last) if last else None,
        "unread_count": unread_query.count(),
        "updated_at": thread.updated_at.isoformat(timespec="minutes"),
    }


def create_message(thread_id, sender_id, body):
    participant = participant_for(thread_id, sender_id)
    if participant is None:
        raise PermissionError("无权访问该会话")
    other = other_participant(thread_id, sender_id)
    if other is None or is_blocked(sender_id, other.user_id):
        raise PermissionError("当前无法发送消息")
    if not isinstance(body, str):
        raise ValueError("消息必须是文本")
    body = body.strip()
    if not body:
        raise ValueError("消息不能为空")
    if len(body) > 4000:
        raise ValueError("单条消息不能超过4000字")
    message = ChatMessage(thread_id=str(thread_id), sender_id=sender_id, body=body)
    thread = ChatThread.query.get(str(thread_id))
    thread.updated_at = datetime.utcnow()
    db.session.add(message)
    db.session.commit()
    return message


def mark_read(thread_id, user_id, message_id=None):
    participant = participant_for(thread_id, user_id)
    if participant is None:
        raise PermissionError("无权访问该会话")
    message = None
    if message_id:
        message = ChatMessage.query.filter_by(id=str(message_id), thread_id=str(thread_id)).first()
    if message is None:
        message = ChatMessage.query.filter_by(thread_id=str(thread_id)).order_by(ChatMessage.created_at.desc()).first()
    if message:
        participant.last_read_message_id = message.id
        db.session.commit()
    return message
