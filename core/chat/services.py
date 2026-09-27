from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from core.models import User, db

from .models import ChatAttachment, ChatAuditLog, ChatMessage, ChatMessageHidden, ChatParticipant, ChatThread, ChatUserSanction, UserBlock
from .rendering import render_markdown


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
    attachment = ChatAttachment.query.filter_by(message_id=message.id).first()
    hidden_text = {"recalled": "消息已撤回", "moderated": "消息因违反规则已被处理", "deleted": "消息已删除"}.get(message.status)
    return {
        "id": message.id,
        "thread_id": message.thread_id,
        "sender_id": message.sender_id,
        "sender_name": message.sender.username if message.sender else "已注销用户",
        "body": hidden_text if hidden_text is not None else message.body,
        "body_html": hidden_text if hidden_text is not None else render_markdown(message.body),
        "sequence": message.sequence,
        "client_message_id": message.client_message_id,
        "message_type": message.message_type,
        "reply_to_id": message.reply_to_id,
        "attachment": ({
            "id": attachment.id, "name": attachment.original_name,
            "mime_type": attachment.mime_type, "size_bytes": attachment.size_bytes,
            "download_url": f"/api/chat/attachments/{attachment.id}",
        } if attachment and message.status not in {"recalled", "deleted"} else None),
        "status": message.status,
        "created_at": message.created_at.isoformat(timespec="seconds"),
        "edited_at": message.edited_at.isoformat(timespec="seconds") if message.edited_at else None,
        "recalled_at": message.recalled_at.isoformat(timespec="seconds") if message.recalled_at else None,
    }


def serialize_thread(thread, user_id):
    other = other_participant(thread.id, user_id)
    hidden_ids = db.session.query(ChatMessageHidden.message_id).filter(ChatMessageHidden.user_id == user_id)
    last = ChatMessage.query.filter(
        ChatMessage.thread_id == thread.id,
        ~ChatMessage.id.in_(hidden_ids),
    ).order_by(ChatMessage.sequence.desc()).first()
    me = participant_for(thread.id, user_id)
    unread_query = ChatMessage.query.filter(
        ChatMessage.thread_id == thread.id,
        ChatMessage.sender_id != user_id,
        ChatMessage.status.in_(("sent", "delivered")),
        ~ChatMessage.id.in_(hidden_ids),
    )
    if me:
        unread_query = unread_query.filter(ChatMessage.sequence > int(me.last_read_sequence or 0))
    return {
        "id": thread.id,
        "other_user": {"id": other.user.id, "username": other.user.username} if other and other.user else None,
        "last_message": serialize_message(last) if last else None,
        "unread_count": unread_query.count(),
        "updated_at": thread.updated_at.isoformat(timespec="minutes"),
    }


def create_message(thread_id, sender_id, body, *, client_message_id=None, reply_to_id=None, message_type="text", attachment=None):
    sanction = ChatUserSanction.query.get(sender_id)
    if sanction and (sanction.banned_at or (sanction.muted_until and sanction.muted_until > datetime.utcnow())):
        raise PermissionError("账号当前被限制发送私信")
    participant = participant_for(thread_id, sender_id)
    if participant is None:
        raise PermissionError("无权访问该会话")
    other = other_participant(thread_id, sender_id)
    if other is None or is_blocked(sender_id, other.user_id):
        raise PermissionError("当前无法发送消息")
    client_message_id = str(client_message_id or "").strip()[:64] or None
    if client_message_id:
        existing = ChatMessage.query.filter_by(sender_id=sender_id, client_message_id=client_message_id).first()
        if existing:
            if existing.thread_id != str(thread_id):
                raise ValueError("client_message_id 已用于其他会话")
            existing._idempotent_replay = True
            return existing
    if not isinstance(body, str):
        raise ValueError("消息必须是文本")
    body = body.strip()
    if not body and attachment is None:
        raise ValueError("消息不能为空")
    if len(body) > 4000:
        raise ValueError("单条消息不能超过4000字")
    # System messages are reserved for trusted server-side workflows. Public
    # HTTP/Socket callers must never be able to impersonate them.
    if message_type not in {"text", "image", "attachment"}:
        raise ValueError("消息类型无效")
    reply = None
    if reply_to_id:
        reply = ChatMessage.query.filter_by(id=str(reply_to_id), thread_id=str(thread_id)).first()
        if reply is None:
            raise ValueError("回复的消息不存在")
    thread = ChatThread.query.filter_by(id=str(thread_id)).with_for_update().first()
    if thread is None:
        raise PermissionError("会话不存在")
    sequence = int(thread.next_sequence or 1)
    thread.next_sequence = sequence + 1
    message = ChatMessage(
        thread_id=str(thread_id), sender_id=sender_id, body=body,
        client_message_id=client_message_id, sequence=sequence,
        message_type=message_type, reply_to_id=reply.id if reply else None,
    )
    thread.updated_at = datetime.utcnow()
    db.session.add(message)
    db.session.flush()
    if attachment:
        db.session.add(ChatAttachment(message_id=message.id, **attachment))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if client_message_id:
            existing = ChatMessage.query.filter_by(sender_id=sender_id, client_message_id=client_message_id).first()
            if existing and existing.thread_id == str(thread_id):
                existing._idempotent_replay = True
                return existing
        raise
    message._idempotent_replay = False
    return message


def mark_read(thread_id, user_id, message_id=None):
    participant = participant_for(thread_id, user_id)
    if participant is None:
        raise PermissionError("无权访问该会话")
    message = None
    if message_id:
        message = ChatMessage.query.filter_by(id=str(message_id), thread_id=str(thread_id)).first()
    if message is None:
        message = ChatMessage.query.filter_by(thread_id=str(thread_id)).order_by(ChatMessage.sequence.desc()).first()
    if message:
        participant.last_read_message_id = message.id
        participant.last_read_sequence = max(participant.last_read_sequence or 0, message.sequence or 0)
        db.session.commit()
    return message


def edit_message(message_id, actor_id, body):
    message = ChatMessage.query.filter_by(id=str(message_id), sender_id=actor_id).first()
    if message is None:
        raise PermissionError("无权编辑该消息")
    if message.status not in {"sent", "delivered"} or message.message_type != "text":
        raise ValueError("该消息不能编辑")
    body = str(body or "").strip()
    if not body or len(body) > 4000:
        raise ValueError("消息不能为空且不能超过4000字")
    message.body, message.edited_at = body, datetime.utcnow()
    db.session.add(ChatAuditLog(actor_id=actor_id, action="edit_message", target_type="message", target_id=message.id))
    db.session.commit()
    return message


def recall_message(message_id, actor_id, seconds=120):
    message = ChatMessage.query.filter_by(id=str(message_id), sender_id=actor_id).first()
    if message is None:
        raise PermissionError("无权撤回该消息")
    if message.status == "recalled":
        return message
    if (datetime.utcnow() - message.created_at).total_seconds() > seconds:
        raise ValueError("已超过可撤回时间")
    message.status, message.recalled_at, message.body = "recalled", datetime.utcnow(), ""
    db.session.add(ChatAuditLog(actor_id=actor_id, action="recall_message", target_type="message", target_id=message.id))
    db.session.commit()
    return message


def hide_message(message_id, user_id):
    message = ChatMessage.query.get(str(message_id))
    if message is None or participant_for(message.thread_id, user_id) is None:
        raise PermissionError("无权操作该消息")
    hidden = ChatMessageHidden.query.filter_by(message_id=message.id, user_id=user_id).first()
    if hidden is None:
        db.session.add(ChatMessageHidden(message_id=message.id, user_id=user_id))
        db.session.commit()
