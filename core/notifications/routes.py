from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from core.models import db

from .models import NotificationDelivery, NotificationOutbox, NotificationPreference, PushDevice
from .services import register_device


notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notifications_bp.get("")
@login_required
def list_notifications():
    rows = db.session.query(NotificationDelivery, NotificationOutbox).join(
        NotificationOutbox, NotificationOutbox.id == NotificationDelivery.outbox_id
    ).filter(
        NotificationDelivery.user_id == current_user.id,
        NotificationDelivery.channel == "in_app",
    ).order_by(NotificationDelivery.created_at.desc()).limit(100).all()
    return jsonify({"notifications": [{
        "id": delivery.id,
        "event_type": outbox.event_type,
        "title": outbox.title,
        "body": outbox.body,
        "route": outbox.route,
        "status": delivery.status,
        "read_at": delivery.read_at.isoformat() if delivery.read_at else None,
        "created_at": delivery.created_at.isoformat(),
    } for delivery, outbox in rows]})


@notifications_bp.post("/<notification_id>/read")
@login_required
def mark_notification_read(notification_id):
    row = NotificationDelivery.query.filter_by(id=notification_id, user_id=current_user.id, channel="in_app").first()
    if row is None:
        return jsonify({"error": "通知不存在"}), 404
    row.read_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"status": "ok"})


@notifications_bp.post("/devices")
@login_required
def add_device():
    data = request.get_json(silent=True) or {}
    try:
        row = register_device(current_user.id, data.get("platform"), data.get("token"))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"status": "ok", "device_id": row.id}), 201


@notifications_bp.delete("/devices/<device_id>")
@login_required
def remove_device(device_id):
    row = PushDevice.query.filter_by(id=device_id, user_id=current_user.id).first()
    if row:
        row.active = False
        db.session.commit()
    return jsonify({"status": "ok"})


@notifications_bp.route("/preferences", methods=["GET", "PUT"])
@login_required
def preferences():
    row = NotificationPreference.query.get(current_user.id)
    if row is None:
        row = NotificationPreference(user_id=current_user.id)
        db.session.add(row)
        db.session.commit()
    if request.method == "PUT":
        data = request.get_json(silent=True) or {}
        for key in ("in_app_enabled", "push_enabled", "generic_lock_screen"):
            if key in data:
                if not isinstance(data[key], bool):
                    return jsonify({"error": f"{key} 必须是布尔值"}), 400
                setattr(row, key, data[key])
        for key in ("quiet_start", "quiet_end"):
            if key in data:
                value = str(data[key] or "").strip()
                try:
                    if value and datetime.strptime(value, "%H:%M").strftime("%H:%M") != value:
                        raise ValueError
                except ValueError:
                    return jsonify({"error": f"{key} 必须使用 HH:MM 格式"}), 400
                setattr(row, key, value or None)
        if "timezone" in data:
            timezone = str(data["timezone"] or "").strip()[:40]
            if not timezone:
                return jsonify({"error": "timezone 不是有效的 IANA 时区"}), 400
            try:
                ZoneInfo(timezone)
            except (ZoneInfoNotFoundError, ValueError):
                return jsonify({"error": "timezone 不是有效的 IANA 时区"}), 400
            row.timezone = timezone
        db.session.commit()
    return jsonify({"in_app_enabled": row.in_app_enabled, "push_enabled": row.push_enabled, "generic_lock_screen": row.generic_lock_screen, "quiet_start": row.quiet_start, "quiet_end": row.quiet_end, "timezone": row.timezone})
