"""Persistence helpers for the multi-turn legal agent.

Messages are redacted before storage.  The small structured draft state is kept
separately so a document can be completed over multiple turns without sending
unredacted personal information to an external model.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Any

from .models import Conversation, ConversationMessage, db
from .privacy import RedactionSession, redact_nested_json


class ConversationNotFound(LookupError):
    pass


def _loads(value: str | None, fallback: Any) -> Any:
    try:
        parsed = json.loads(value or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    return parsed


def _title_from(text: str) -> str:
    compact = " ".join(str(text or "").split())
    return (compact[:38] or "新法律咨询") + ("…" if len(compact) > 38 else "")


def get_or_create_conversation(
    user_id: int,
    conversation_id: str | None = None,
    title_hint: str = "",
) -> tuple[Conversation, bool]:
    if conversation_id:
        conversation = Conversation.query.filter_by(
            id=str(conversation_id), user_id=user_id
        ).first()
        if conversation is None:
            raise ConversationNotFound("会话不存在或无权访问")
        return conversation, False

    title_session = RedactionSession()
    conversation = Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=_title_from(title_session.redact(title_hint or "")),
        state_json="{}",
    )
    db.session.add(conversation)
    db.session.commit()
    return conversation, True


def load_state(conversation: Conversation) -> dict[str, Any]:
    state = _loads(conversation.state_json, {})
    return state if isinstance(state, dict) else {}


def save_state(conversation: Conversation, state: dict[str, Any]) -> None:
    session = RedactionSession()
    safe_state = redact_nested_json(state or {}, session)
    conversation.state_json = json.dumps(safe_state, ensure_ascii=False)
    conversation.updated_at = datetime.utcnow()
    db.session.commit()


def add_message(
    conversation: Conversation,
    role: str,
    content: str,
    *,
    attachment: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
) -> ConversationMessage:
    if role not in {"user", "assistant"}:
        raise ValueError("unsupported conversation role")

    session = RedactionSession()
    safe_content = session.redact(str(content or ""))
    safe_attachment = redact_nested_json(attachment or {}, session)
    # Never put extracted document text into the attachment audit metadata.
    if isinstance(safe_attachment, dict):
        safe_attachment.pop("text", None)
        safe_attachment.pop("extracted_text", None)
    safe_result = redact_nested_json(result or {}, session)

    message = ConversationMessage(
        conversation_id=conversation.id,
        role=role,
        content=safe_content[:20000],
        attachment_json=json.dumps(safe_attachment, ensure_ascii=False) if safe_attachment else None,
        result_json=json.dumps(safe_result, ensure_ascii=False) if safe_result else None,
    )
    conversation.updated_at = datetime.utcnow()
    db.session.add(message)
    db.session.commit()
    return message


def conversation_context(conversation: Conversation, limit: int = 8) -> str:
    rows = (
        ConversationMessage.query
        .filter_by(conversation_id=conversation.id)
        .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
        .limit(max(1, min(int(limit), 20)))
        .all()
    )
    rows.reverse()
    labels = {"user": "用户", "assistant": "明鉴"}
    rendered = []
    for turn_index, row in enumerate(rows, 1):
        # Citation ids are scoped to one response.  Do not leak an old [L1]
        # into a new retrieval/audit round, and namespace redaction markers so
        # two turns' independently-created [姓名_1] values are not conflated.
        content = re.sub(r"\[L\d+\]", "[历史引用已省略]", row.content[:3000])
        content = re.sub(
            r"\[([\u4e00-\u9fffA-Za-z]+)_([0-9]+)\]",
            rf"[T{turn_index}_\1_\2]",
            content,
        )
        rendered.append(f"{labels.get(row.role, row.role)}：{content}")
    return "\n".join(rendered)


def serialize_conversation(
    conversation: Conversation,
    *,
    include_messages: bool = False,
    message_limit: int = 60,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(timespec="minutes"),
        "updated_at": conversation.updated_at.isoformat(timespec="minutes"),
    }
    if include_messages:
        rows = (
            ConversationMessage.query
            .filter_by(conversation_id=conversation.id)
            .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
            .limit(max(1, min(int(message_limit), 200)))
            .all()
        )
        payload["messages"] = [
            {
                "id": row.id,
                "role": row.role,
                "content": row.content,
                "attachment": _loads(row.attachment_json, {}),
                "result": _loads(row.result_json, {}),
                "created_at": row.created_at.isoformat(timespec="minutes"),
            }
            for row in rows
        ]
    return payload


def list_conversations(user_id: int, limit: int = 30) -> list[dict[str, Any]]:
    conversations = (
        Conversation.query
        .filter_by(user_id=user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(max(1, min(int(limit), 100)))
        .all()
    )
    return [serialize_conversation(item) for item in conversations]


def delete_conversation(user_id: int, conversation_id: str) -> bool:
    conversation = Conversation.query.filter_by(
        id=str(conversation_id), user_id=user_id
    ).first()
    if conversation is None:
        return False
    db.session.delete(conversation)
    db.session.commit()
    return True
