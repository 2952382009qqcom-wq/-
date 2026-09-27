import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError

from core.models import db

from .adapters import ADAPTERS, PermanentDeliveryError, TemporaryDeliveryError
from .crypto import decrypt_token, encrypt_token, token_hash
from .models import NotificationDelivery, NotificationOutbox, NotificationPreference, PushDevice


def register_device(user_id, platform, token):
    platform, token = str(platform or "").lower(), str(token or "").strip()
    if platform not in ADAPTERS or not token or len(token) > 4096:
        raise ValueError("设备平台或令牌无效")
    digest = token_hash(token)
    # A physical push token must belong to only the currently authenticated
    # account. Otherwise signing out and into another account on the same
    # device could leak the previous account's legal notifications.
    PushDevice.query.filter(
        PushDevice.token_hash == digest,
        PushDevice.user_id != user_id,
    ).update({"active": False}, synchronize_session=False)
    row = PushDevice.query.filter_by(user_id=user_id, token_hash=digest).first()
    if row is None:
        row = PushDevice(user_id=user_id, platform=platform, token_hash=digest, encrypted_token=encrypt_token(token))
        db.session.add(row)
    else:
        row.platform, row.encrypted_token, row.active = platform, encrypt_token(token), True
        row.last_seen_at = datetime.utcnow()
    db.session.commit()
    return row


def enqueue_notification(user_id, event_type, title, body, route="/", payload=None, idempotency_key=None):
    key = str(idempotency_key or f"{event_type}:{user_id}:{datetime.utcnow().isoformat()}")[:120]
    existing = NotificationOutbox.query.filter_by(idempotency_key=key).first()
    if existing:
        return existing
    if event_type == "chat_message":
        aggregate = NotificationOutbox.query.filter(
            NotificationOutbox.user_id == user_id,
            NotificationOutbox.event_type == "chat_message",
            NotificationOutbox.route == str(route or "/")[:255],
            NotificationOutbox.status.in_(("pending", "retry")),
            NotificationOutbox.created_at >= datetime.utcnow() - timedelta(minutes=5),
        ).order_by(NotificationOutbox.created_at.desc()).first()
        if aggregate:
            data = json.loads(aggregate.payload_json or "{}")
            data["aggregated_count"] = int(data.get("aggregated_count", 1)) + 1
            aggregate.title = "收到多条新私信"
            aggregate.body = "打开明鉴查看消息"
            aggregate.payload_json = json.dumps(data, ensure_ascii=False)
            db.session.commit()
            return aggregate
    row = NotificationOutbox(
        user_id=user_id, event_type=str(event_type)[:40], title=str(title)[:120], body=str(body)[:500],
        route=str(route or "/")[:255], payload_json=json.dumps(payload or {}, ensure_ascii=False), idempotency_key=key,
    )
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = NotificationOutbox.query.filter_by(idempotency_key=key).first()
        if existing is not None:
            return existing
        raise
    return row


def _push_payload(row, preference):
    generic = preference is None or preference.generic_lock_screen
    return {
        "notification": {"title": "明鉴有新消息" if generic else row.title, "body": "打开明鉴查看详情" if generic else row.body},
        "data": {"route": row.route, "event_type": row.event_type, "outbox_id": row.id},
    }


def _quiet_now(preference):
    if preference is None or not preference.quiet_start or not preference.quiet_end:
        return False
    try:
        local = datetime.now(ZoneInfo(preference.timezone)).strftime("%H:%M")
    except ZoneInfoNotFoundError:
        local = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%H:%M")
    start, end = preference.quiet_start, preference.quiet_end
    return start <= local < end if start < end else (local >= start or local < end)


def process_outbox_item(outbox_id, now=None):
    now = now or datetime.utcnow()
    row = NotificationOutbox.query.get(str(outbox_id))
    if row is None or row.status in {"sent", "failed"}:
        return row
    # Claim with a lease before contacting an external provider. Multiple
    # Celery workers may see the same due row, but only one can transition it
    # to processing. An expired lease is recoverable after a worker crash.
    claimed = NotificationOutbox.query.filter(
        NotificationOutbox.id == row.id,
        or_(
            and_(
                NotificationOutbox.status.in_(("pending", "retry")),
                NotificationOutbox.next_attempt_at <= now,
            ),
            and_(
                NotificationOutbox.status == "processing",
                NotificationOutbox.next_attempt_at <= now,
            ),
        ),
    ).update({
        "status": "processing",
        "next_attempt_at": now + timedelta(minutes=5),
    }, synchronize_session=False)
    db.session.commit()
    if not claimed:
        db.session.refresh(row)
        return row
    row = NotificationOutbox.query.get(str(outbox_id))
    preference = NotificationPreference.query.get(row.user_id)
    # In-app delivery is durable even when push is disabled or unavailable.
    in_app = NotificationDelivery.query.filter_by(outbox_id=row.id, channel="in_app").first()
    if in_app is None and (preference is None or preference.in_app_enabled):
        db.session.add(NotificationDelivery(outbox_id=row.id, user_id=row.user_id, channel="in_app", status="delivered", delivered_at=now))
    # Quiet hours delay only lock-screen/device pushes; users who open the app
    # should still see the durable in-app notification immediately.
    if _quiet_now(preference):
        row.status = "retry"
        row.next_attempt_at = now + timedelta(minutes=30)
        db.session.commit()
        return row
    devices = PushDevice.query.filter_by(user_id=row.user_id, active=True).all()
    temporary = False
    if preference is None or preference.push_enabled:
        for device in devices:
            delivery = NotificationDelivery.query.filter_by(outbox_id=row.id, channel=f"push:{device.id}").first()
            if delivery and delivery.status == "delivered":
                continue
            delivery = delivery or NotificationDelivery(outbox_id=row.id, user_id=row.user_id, channel=f"push:{device.id}")
            db.session.add(delivery)
            try:
                delivery.provider_message_id = ADAPTERS[device.platform].send(decrypt_token(device.encrypted_token), _push_payload(row, preference))
                delivery.status, delivery.delivered_at = "delivered", now
            except PermanentDeliveryError as error:
                device.active, delivery.status, delivery.error_code = False, "failed", str(error)[:80]
            except ValueError:
                device.active, delivery.status, delivery.error_code = False, "failed", "token_decryption_failed"
            except TemporaryDeliveryError as error:
                temporary, delivery.status, delivery.error_code = True, "retry", str(error)[:80]
    if temporary and row.retry_count < row.max_retries:
        row.retry_count += 1
        row.status = "retry"
        row.next_attempt_at = now + timedelta(seconds=min(3600, 2 ** row.retry_count * 30))
        row.last_error = "temporary_delivery_failure"
    elif temporary:
        row.status, row.processed_at, row.last_error = "failed", now, "retry_limit_reached"
    else:
        row.status, row.processed_at, row.last_error = "sent", now, ""
    db.session.commit()
    return row
