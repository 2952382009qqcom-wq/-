from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from core.models import db

from .models import NotificationDelivery, NotificationPreference, PushDevice
from .services import register_device


notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notifications_bp.get("")
@login_required
def list_notifications():
    rows = NotificationDelivery.query.filter_by(user_id=current_user.id, channel="in_app").order_by(NotificationDelivery.created_at.desc()).limit(100).all()
    return jsonify({"notifications": [{"id": row.id, "status": row.status, "read_at": row.read_at.isoformat() if row.read_at else None, "created_at": row.created_at.isoformat()} for row in rows]})


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
                setattr(row, key, bool(data[key]))
        for key in ("quiet_start", "quiet_end", "timezone"):
            if key in data:
                setattr(row, key, str(data[key] or "")[:40] or None)
        db.session.commit()
    return jsonify({"in_app_enabled": row.in_app_enabled, "push_enabled": row.push_enabled, "generic_lock_screen": row.generic_lock_screen, "quiet_start": row.quiet_start, "quiet_end": row.quiet_end, "timezone": row.timezone})
