from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from core.models import db, User, AnalysisRecord
from datetime import datetime, timedelta
from sqlalchemy import func

auth_bp = Blueprint('auth', __name__)


def user_info(user):
    return {
        'id': user.id,
        'username': user.username,
        'is_admin': user.is_admin,
        'is_approved': user.is_approved,
        'approval_requested': user.approval_requested,
        'approval_requested_at': user.approval_requested_at.isoformat() if user.approval_requested_at else '',
        'llm_model': user.llm_model or '',
        'llm_base_url': user.llm_base_url or '',
        'has_llm_api_key': bool(user.llm_api_key),
    }


@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or len(username) < 3:
        return jsonify({'error': '用户名至少3个字符'}), 400
    if not password or len(password) < 6:
        return jsonify({'error': '密码至少6个字符'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已存在'}), 409

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        is_approved=False,
        approval_requested=False,
    )
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return jsonify({'status': 'ok', 'user': user_info(user)})


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': '用户名或密码错误'}), 401

    login_user(user)
    return jsonify({'status': 'ok', 'user': user_info(user)})


@auth_bp.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'status': 'ok'})


@auth_bp.route('/api/auth/status', methods=['GET'])
def auth_status():
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'user': user_info(current_user)})
    return jsonify({'authenticated': False})


@auth_bp.route('/api/auth/request-approval', methods=['POST'])
@login_required
def request_approval():
    if current_user.is_approved or current_user.is_admin:
        return jsonify({'error': '您已获得 API 使用权限'}), 400
    if current_user.approval_requested:
        return jsonify({'error': '您已提交申请，请等待管理员审核'}), 400
    current_user.approval_requested = True
    current_user.approval_requested_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'ok', 'message': '申请已提交，请等待管理员审核'})


# ===== Admin endpoints =====

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*a, **kw):
        if not current_user.is_authenticated:
            return jsonify({'error': '请先登录'}), 401
        if not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*a, **kw)
    return decorated


@auth_bp.route('/api/admin/pending-users', methods=['GET'])
@login_required
@admin_required
def list_pending_users():
    users = User.query.filter_by(approval_requested=True, is_approved=False, is_admin=False).all()
    return jsonify({
        'users': [{
            'id': u.id,
            'username': u.username,
            'created_at': u.created_at.isoformat(),
            'approval_requested_at': u.approval_requested_at.isoformat() if u.approval_requested_at else '',
        } for u in users],
    })


@auth_bp.route('/api/admin/approve/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    user.is_approved = True
    user.approval_requested = False
    db.session.commit()
    return jsonify({'status': 'ok', 'message': f'用户 {user.username} 已通过审核'})


@auth_bp.route('/api/admin/reject/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reject_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    user.approval_requested = False
    db.session.commit()
    return jsonify({'status': 'ok', 'message': f'已驳回用户 {user.username} 的申请'})


@auth_bp.route('/api/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    if user.is_admin:
        return jsonify({'error': '不能删除管理员账号'}), 400
    AnalysisRecord.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({'status': 'ok', 'message': f'已删除用户 {user.username}'})


@auth_bp.route('/api/admin/set-model/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def set_user_model(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    data = request.get_json(silent=True) or {}
    user.llm_model = data.get('llm_model', '').strip() or None
    db.session.commit()
    return jsonify({'status': 'ok', 'message': f'已更新用户 {user.username} 的模型'})


@auth_bp.route('/api/admin/revoke/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def revoke_user(user_id):
    """取消用户的使用权限"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    if user.is_admin:
        return jsonify({'error': '不能取消管理员的权限'}), 400
    user.is_approved = False
    user.approval_requested = False
    user.llm_model = None
    db.session.commit()
    return jsonify({'status': 'ok', 'message': f'已取消用户 {user.username} 的使用权限'})


@auth_bp.route('/api/admin/all-users', methods=['GET'])
@login_required
@admin_required
def list_all_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({
        'users': [user_info(u) for u in users],
    })


@auth_bp.route('/api/admin/metrics', methods=['GET'])
@login_required
@admin_required
def admin_metrics():
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today - timedelta(days=6)

    module_rows = (
        db.session.query(AnalysisRecord.module_type, func.count(AnalysisRecord.id))
        .group_by(AnalysisRecord.module_type)
        .all()
    )
    recent_module_rows = (
        db.session.query(AnalysisRecord.module_type, func.count(AnalysisRecord.id))
        .filter(AnalysisRecord.created_at >= week_start)
        .group_by(AnalysisRecord.module_type)
        .all()
    )

    return jsonify({
        'users': {
            'total': User.query.count(),
            'approved': User.query.filter_by(is_approved=True, is_admin=False).count(),
            'pending': User.query.filter_by(approval_requested=True, is_approved=False, is_admin=False).count(),
            'personal_api': User.query.filter(User.llm_api_key.isnot(None), User.is_admin == False).count(),
        },
        'usage': {
            'total': AnalysisRecord.query.count(),
            'today': AnalysisRecord.query.filter(AnalysisRecord.created_at >= today).count(),
            'last_7_days': AnalysisRecord.query.filter(AnalysisRecord.created_at >= week_start).count(),
            'by_module': {module or 'unknown': count for module, count in module_rows},
            'recent_by_module': {module or 'unknown': count for module, count in recent_module_rows},
        },
    })
