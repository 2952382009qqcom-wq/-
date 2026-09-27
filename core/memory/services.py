import json
import math
import hashlib
import re
from datetime import datetime

from core.models import Conversation, ConversationMessage, db
from core.privacy import RedactionSession
from core.taxonomy import infer_legal_domain

from .models import ConversationSummary, UserMemoryAudit, UserMemoryEmbedding, UserMemoryItem, UserMemorySetting


ALLOWED_MEMORY_TYPES = {"preference", "stable_fact", "ongoing_matter", "communication_style"}
SENSITIVE_PATTERNS = re.compile(r"身份证|银行卡|密码|口令|家庭住址|病历|手机号|微信号|第三方隐私")


def _local_vector(value, dimensions=64):
    vector = [0.0] * dimensions
    for token in re.findall(r"[\u4e00-\u9fff]{1,2}|[a-zA-Z0-9]{3,}", str(value or "").lower()):
        bucket = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:4], "big") % dimensions
        vector[bucket] += 1.0
    norm = math.sqrt(sum(item * item for item in vector)) or 1.0
    return [round(item / norm, 6) for item in vector]


def build_missing_embeddings(limit=200):
    rows = UserMemoryItem.query.outerjoin(UserMemoryEmbedding, UserMemoryEmbedding.memory_id == UserMemoryItem.id).filter(
        UserMemoryItem.deleted_at.is_(None), UserMemoryEmbedding.id.is_(None)
    ).limit(min(int(limit), 1000)).all()
    for row in rows:
        db.session.add(UserMemoryEmbedding(memory_id=row.id, model="local-hash-v1", vector_json=json.dumps(_local_vector(row.content))))
    db.session.commit()
    return len(rows)


def setting_for(user_id):
    return UserMemorySetting.query.get(user_id)


def memory_enabled(user_id):
    row = setting_for(user_id)
    return bool(row and row.enabled)


def set_memory_enabled(user_id, enabled):
    row = setting_for(user_id) or UserMemorySetting(user_id=user_id)
    row.enabled = bool(enabled)
    db.session.add(row)
    db.session.add(UserMemoryAudit(user_id=user_id, action="enable" if enabled else "disable"))
    db.session.commit()
    return row


def create_memory(user_id, content, memory_type, *, conversation_id=None, message_id=None, reason="用户主动保存"):
    if not memory_enabled(user_id):
        raise ValueError("长期记忆默认关闭，请先主动开启")
    memory_type = str(memory_type or "")
    if memory_type not in ALLOWED_MEMORY_TYPES:
        raise ValueError("不支持的记忆类型")
    safe = sanitize_memory_content(content)

    conversation_id = str(conversation_id).strip() if conversation_id else None
    owned_conversation = None
    if conversation_id:
        owned_conversation = Conversation.query.filter_by(id=conversation_id, user_id=user_id).first()
        if owned_conversation is None:
            raise ValueError("来源对话不存在或不属于当前用户")
    if message_id is not None:
        try:
            message_id = int(message_id)
        except (TypeError, ValueError):
            raise ValueError("来源消息无效") from None
        source_message = ConversationMessage.query.join(
            Conversation, Conversation.id == ConversationMessage.conversation_id
        ).filter(
            ConversationMessage.id == message_id,
            Conversation.user_id == user_id,
        ).first()
        if source_message is None:
            raise ValueError("来源消息不存在或不属于当前用户")
        if owned_conversation and source_message.conversation_id != owned_conversation.id:
            raise ValueError("来源消息不属于所选对话")
        conversation_id = source_message.conversation_id

    item = UserMemoryItem(
        user_id=user_id, memory_type=memory_type, legal_domain=infer_legal_domain(safe), content=safe,
        source_conversation_id=conversation_id, source_message_id=message_id, reason=str(reason)[:240],
    )
    db.session.add(item)
    db.session.flush()
    db.session.add(UserMemoryAudit(user_id=user_id, memory_id=item.id, action="create", reason=item.reason))
    db.session.commit()
    return item


def sanitize_memory_content(content):
    if not isinstance(content, str):
        raise ValueError("记忆内容必须是文本")
    content = content.strip()
    if not content or len(content) > 1000 or SENSITIVE_PATTERNS.search(content):
        raise ValueError("内容为空、过长或包含不应长期保存的敏感信息")
    safe = RedactionSession().redact(content)
    return safe


def retrieve_memories(user_id, query, legal_domain="", limit=5):
    if not memory_enabled(user_id):
        return []
    rows = UserMemoryItem.query.filter(
        UserMemoryItem.user_id == user_id, UserMemoryItem.deleted_at.is_(None),
        (UserMemoryItem.expires_at.is_(None) | (UserMemoryItem.expires_at > datetime.utcnow())),
    ).all()
    terms = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]{3,}", str(query or "").lower()))
    ranked = []
    query_vector = _local_vector(query)
    for row in rows:
        row_terms = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]{3,}", row.content.lower()))
        score = len(terms & row_terms) + (2 if legal_domain and row.legal_domain == legal_domain else 0)
        embedding = UserMemoryEmbedding.query.filter_by(memory_id=row.id).first()
        if embedding:
            try:
                vector = json.loads(embedding.vector_json)
                score += max(0.0, sum(a * b for a, b in zip(query_vector, vector)))
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        if score:
            ranked.append((score, row))
    chosen = [row for _, row in sorted(ranked, key=lambda pair: (pair[0], pair[1].created_at), reverse=True)[:limit]]
    for row in chosen:
        row.last_used_at = datetime.utcnow()
        db.session.add(UserMemoryAudit(user_id=user_id, memory_id=row.id, action="retrieve", reason="与当前任务相关"))
    if chosen:
        db.session.commit()
    return chosen


def latest_summary(conversation_id, user_id):
    return ConversationSummary.query.filter_by(conversation_id=conversation_id, user_id=user_id).order_by(ConversationSummary.source_end_message_id.desc()).first()


def rebuild_summary(conversation_id):
    conversation = Conversation.query.get(str(conversation_id))
    if conversation is None:
        return {"status": "missing"}
    rows = ConversationMessage.query.filter_by(conversation_id=conversation.id).order_by(ConversationMessage.id.asc()).all()
    if len(rows) < 10:
        return {"status": "below_threshold"}
    source = rows[:-6]
    if not source:
        return {"status": "below_threshold"}
    existing = ConversationSummary.query.filter_by(
        conversation_id=conversation.id, source_start_message_id=source[0].id, source_end_message_id=source[-1].id,
    ).first()
    if existing:
        return {"status": "exists", "id": existing.id}
    facts, conflicts = [], []
    for row in source:
        content = " ".join(row.content.split())[:500]
        if content:
            facts.append(f"{row.role}#{row.id}: {content}")
    # Extractive only: all text remains traceable to source message ids. Flag
    # obvious corrections instead of deciding which statement is true.
    for row in source:
        if re.search(r"不是|更正|改为|说错了|取消", row.content):
            conflicts.append({"message_id": row.id, "marker": "用户表达了否定或更正，请以较新消息核实"})
    summary = ConversationSummary(
        conversation_id=conversation.id, user_id=conversation.user_id,
        summary="\n".join(facts)[-12000:], source_start_message_id=source[0].id,
        source_end_message_id=source[-1].id, conflicts_json=json.dumps(conflicts, ensure_ascii=False),
    )
    db.session.add(summary)
    db.session.commit()
    return {"status": "created", "id": summary.id}


def build_memory_context(user_id, conversation_id, question):
    domain = infer_legal_domain(question)
    memories = retrieve_memories(user_id, question, domain)
    summary = latest_summary(conversation_id, user_id)
    return {
        "summary": summary.summary if summary else "无",
        "memories": "\n".join(f"- ({row.memory_type}) {row.content}" for row in memories) or "无",
    }
