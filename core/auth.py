from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from core.models import db, User, AnalysisRecord
from core.moderation.audit import log_admin_action
from datetime import datetime, timedelta
import os
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from core.model_settings import validate_model_name

auth_bp = Blueprint('auth', __name__)


def _text_field(data, key, default=''):
    value = data.get(key, default) if isinstance(data, dict) else default
    return value.strip() if isinstance(value, str) else None


def free_api_limit():
    try:
        return max(0, int(os.getenv('FREE_API_LIMIT', '10')))
    except ValueError:
        return 10


def user_info(user):
    limit = free_api_limit()
    used = max(0, int(user.free_api_used or 0))
    unlimited = bool(user.is_approved or user.is_admin or user.llm_api_key)
    return {
        'id': user.id,
        'username': user.username,
        'is_admin': user.is_admin,
        'is_approved': user.is_approved,
        'is_test_account': bool(getattr(user, 'is_test_account', False)),
        'approval_requested': user.approval_requested,
        'approval_requested_at': user.approval_requested_at.isoformat() if user.approval_requested_at else '',
        'llm_model': user.llm_model or '',
        'llm_base_url': user.llm_base_url or '',
        'has_llm_api_key': bool(user.llm_api_key),
        'role': 'admin' if user.is_admin else 'user',
        'ai_unlimited': unlimited,
        'quota_mode': 'unlimited' if unlimited else 'trial',
        'free_api_limit': limit,
        'free_api_used': used,
        'free_api_remaining': None if unlimited else max(0, limit - used),
    }


@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = _text_field(data, 'username')
    password = _text_field(data, 'password')

    if username is None or password is None:
        return jsonify({'error': '用户名和密码必须是文本'}), 400
    if not username or len(username) < 3:
        return jsonify({'error': '用户名至少3个字符'}), 400
    if not password or len(password) < 6:
        return jsonify({'error': '密码至少6个字符'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已存在'}), 409

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        is_admin=False,
        is_approved=False,
        approval_requested=False,
        free_api_used=0,
    )
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return jsonify({'status': 'ok', 'user': user_info(user)})


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = _text_field(data, 'username')
    password = _text_field(data, 'password')

    if username is None or password is None:
        return jsonify({'error': '用户名和密码必须是文本'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': '用户名或密码错误'}), 401

    if user.is_admin:
        return jsonify({'error': '请从管理员入口登录', 'code': 'ADMIN_LOGIN_REQUIRED'}), 403

    login_user(user)
    return jsonify({'status': 'ok', 'user': user_info(user)})


@auth_bp.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or {}
    username = _text_field(data, 'username')
    password = _text_field(data, 'password')

    if username is None or password is None:
        return jsonify({'error': '用户名和密码必须是文本'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': '用户名或密码错误'}), 401
    if not user.is_admin:
        return jsonify({'error': '该账号没有管理员权限', 'code': 'ADMIN_ACCOUNT_REQUIRED'}), 403

    login_user(user)
    log_admin_action('admin_login', target_type='user', target_id=str(user.id))
    db.session.commit()
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


@auth_bp.route('/api/admin/profile', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_profile():
    if request.method == 'GET':
        return jsonify({'user': user_info(current_user)})

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': '请求内容必须是对象'}), 400
    if any(key in data for key in ('is_admin', 'role', 'is_approved')):
        return jsonify({'error': '账号角色和使用权限不可在资料页修改'}), 400

    current_password = _text_field(data, 'current_password')
    username = _text_field(data, 'username')
    password = _text_field(data, 'password')
    if current_password is None or username is None or password is None:
        return jsonify({'error': '用户名和密码必须是文本'}), 400
    if not current_password:
        return jsonify({'error': '请提供当前密码'}), 400
    if not check_password_hash(current_user.password_hash, current_password):
        return jsonify({'error': '当前密码错误', 'code': 'CURRENT_PASSWORD_INCORRECT'}), 401
    if username and (len(username) < 3 or len(username) > 80):
        return jsonify({'error': '用户名需为3至80个字符'}), 400
    if username and User.query.filter(User.username == username, User.id != current_user.id).first():
        return jsonify({'error': '用户名已存在'}), 409

    # All checks precede mutation, and this endpoint only edits the signed-in
    # administrator's credentials. User ids and role fields are never assigned.
    if username:
        current_user.username = username
    if password:
        current_user.password_hash = generate_password_hash(password)
    log_admin_action('admin_profile_update', target_type='user', target_id=str(current_user.id), detail='管理员修改本人账号资料')
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': '用户名已存在'}), 409
    return jsonify({'status': 'ok', 'user': user_info(current_user)})


@auth_bp.route('/api/admin/test-users', methods=['POST'])
@login_required
@admin_required
def create_test_user():
    data = request.get_json(silent=True) or {}
    username = _text_field(data, 'username')
    password = _text_field(data, 'password')
    if username is None or password is None:
        return jsonify({'error': '用户名和密码必须是文本'}), 400
    if not username or len(username) < 3 or len(username) > 80:
        return jsonify({'error': '用户名需为3至80个字符'}), 400
    if not password:
        return jsonify({'error': '测试账号密码不能为空'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已存在，请为测试账号使用独立用户名'}), 409

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        is_admin=False,
        is_approved=True,
        is_test_account=True,
        approval_requested=False,
        free_api_used=0,
    )
    db.session.add(user)
    log_admin_action('test_user_create', target_type='user', target_id=username, detail='创建独立普通测试账号')
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': '用户名已存在，请为测试账号使用独立用户名'}), 409
    return jsonify({'status': 'ok', 'user': user_info(user)}), 201


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
    if user.is_admin:
        return jsonify({'error': '管理员账号不能通过普通用户审核接口修改'}), 400
    user.is_approved = True
    user.approval_requested = False
    log_admin_action('user_approve', target_type='user', target_id=str(user.id), detail=f'通过 {user.username}')
    db.session.commit()
    return jsonify({'status': 'ok', 'message': f'用户 {user.username} 已通过审核'})


@auth_bp.route('/api/admin/reject/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reject_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    if user.is_admin:
        return jsonify({'error': '管理员账号不能通过普通用户审核接口修改'}), 400
    user.approval_requested = False
    log_admin_action('user_reject', target_type='user', target_id=str(user.id), detail=f'驳回 {user.username}')
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
    # Keep public discussions useful while removing the account link, and
    # remove private/personal records that should not survive account deletion.
    from core.cases.models import CaseFavorite, LegalCase
    from core.chat.models import (
        ChatAttachment,
        ChatAuditLog,
        ChatMessage,
        ChatMessageHidden,
        ChatParticipant,
        ChatReport,
        ChatThread,
        ChatUserSanction,
        UserBlock,
    )
    from core.chat.storage import LocalAttachmentStorage
    from core.community.models import (
        CommunityComment,
        CommunityCommentLike,
        CommunityPost,
        CommunityPostFavorite,
        CommunityPostLike,
        CommunityReport,
        ModerationAction,
        Notification,
    )
    from core.memory.models import (
        ConversationSummary,
        UserMemoryAudit,
        UserMemoryEmbedding,
        UserMemoryItem,
        UserMemorySetting,
    )
    from core.models import Conversation, ConversationMessage
    from core.notifications.models import (
        NotificationDelivery,
        NotificationOutbox,
        NotificationPreference,
        PushDevice,
    )
    from core.recommendations.models import RecommendationImpression, UserActivityEvent, UserInterestProfile

    thread_ids = [row.thread_id for row in ChatParticipant.query.filter_by(user_id=user.id).all()]
    attachment_keys = []
    if thread_ids:
        message_ids = [row[0] for row in db.session.query(ChatMessage.id).filter(ChatMessage.thread_id.in_(thread_ids)).all()]
        if message_ids:
            attachment_keys = [row[0] for row in db.session.query(ChatAttachment.storage_key).filter(ChatAttachment.message_id.in_(message_ids)).all()]
            ChatReport.query.filter(ChatReport.message_id.in_(message_ids)).delete(synchronize_session=False)
            ChatMessageHidden.query.filter(ChatMessageHidden.message_id.in_(message_ids)).delete(synchronize_session=False)
            ChatAttachment.query.filter(ChatAttachment.message_id.in_(message_ids)).delete(synchronize_session=False)
        ChatMessage.query.filter(ChatMessage.thread_id.in_(thread_ids)).delete(synchronize_session=False)
        ChatParticipant.query.filter(ChatParticipant.thread_id.in_(thread_ids)).delete(synchronize_session=False)
        ChatThread.query.filter(ChatThread.id.in_(thread_ids)).delete(synchronize_session=False)
    ChatReport.query.filter_by(reporter_id=user.id).delete(synchronize_session=False)
    ChatAuditLog.query.filter_by(actor_id=user.id).update({"actor_id": None}, synchronize_session=False)
    ChatUserSanction.query.filter_by(moderator_id=user.id).update({"moderator_id": None}, synchronize_session=False)
    ChatUserSanction.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    UserBlock.query.filter(
        (UserBlock.blocker_id == user.id) | (UserBlock.blocked_id == user.id)
    ).delete(synchronize_session=False)

    conversation_ids = [row[0] for row in db.session.query(Conversation.id).filter_by(user_id=user.id).all()]
    conversation_message_ids = []
    if conversation_ids:
        conversation_message_ids = [row[0] for row in db.session.query(ConversationMessage.id).filter(
            ConversationMessage.conversation_id.in_(conversation_ids)
        ).all()]
        UserMemoryItem.query.filter(UserMemoryItem.source_conversation_id.in_(conversation_ids)).update(
            {"source_conversation_id": None}, synchronize_session=False
        )
    if conversation_message_ids:
        UserMemoryItem.query.filter(UserMemoryItem.source_message_id.in_(conversation_message_ids)).update(
            {"source_message_id": None}, synchronize_session=False
        )
    memory_ids = [row[0] for row in db.session.query(UserMemoryItem.id).filter_by(user_id=user.id).all()]
    if memory_ids:
        UserMemoryEmbedding.query.filter(UserMemoryEmbedding.memory_id.in_(memory_ids)).delete(synchronize_session=False)
    UserMemoryAudit.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    UserMemoryItem.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    UserMemorySetting.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    ConversationSummary.query.filter_by(user_id=user.id).delete(synchronize_session=False)

    outbox_ids = [row[0] for row in db.session.query(NotificationOutbox.id).filter_by(user_id=user.id).all()]
    if outbox_ids:
        NotificationDelivery.query.filter(NotificationDelivery.outbox_id.in_(outbox_ids)).delete(synchronize_session=False)
    NotificationDelivery.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    NotificationOutbox.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    NotificationPreference.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    PushDevice.query.filter_by(user_id=user.id).delete(synchronize_session=False)

    CommunityPost.query.filter_by(author_id=user.id).update({"author_id": None}, synchronize_session=False)
    CommunityComment.query.filter_by(author_id=user.id).update({"author_id": None}, synchronize_session=False)
    CommunityComment.query.filter_by(reply_to_user_id=user.id).update({"reply_to_user_id": None}, synchronize_session=False)
    Notification.query.filter_by(actor_id=user.id).update({"actor_id": None}, synchronize_session=False)
    ModerationAction.query.filter_by(moderator_id=user.id).update({"moderator_id": None}, synchronize_session=False)
    LegalCase.query.filter_by(created_by=user.id).update({"created_by": None}, synchronize_session=False)

    for model in (
        CommunityPostLike,
        CommunityCommentLike,
        CommunityPostFavorite,
        CommunityReport,
        Notification,
        CaseFavorite,
        UserActivityEvent,
        RecommendationImpression,
        UserInterestProfile,
    ):
        column = "reporter_id" if model is CommunityReport else "user_id"
        model.query.filter_by(**{column: user.id}).delete(synchronize_session=False)
    AnalysisRecord.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    log_admin_action('user_delete', target_type='user', target_id=str(user.id), detail=f'删除 {user.username}')
    db.session.delete(user)
    db.session.commit()
    storage = LocalAttachmentStorage()
    for key in attachment_keys:
        try:
            storage.delete(key)
        except OSError:
            # The account and database rows are already deleted; a storage
            # lifecycle job can retry removal without restoring private data.
            pass
    return jsonify({'status': 'ok', 'message': f'已删除用户 {user.username}'})


@auth_bp.route('/api/admin/set-model/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def set_user_model(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    if user.is_admin:
        return jsonify({'error': '管理员账号不能通过普通用户模型接口修改'}), 400
    data = request.get_json(silent=True) or {}
    llm_model = _text_field(data, 'llm_model')
    if llm_model is None:
        return jsonify({'error': '模型名称必须是文本'}), 400
    if llm_model:
        try:
            llm_model = validate_model_name(llm_model)
        except ValueError as error:
            return jsonify({'error': str(error)}), 400
    user.llm_model = llm_model or None
    log_admin_action('user_set_model', target_type='user', target_id=str(user.id), detail=f'{user.username} → {llm_model or "默认"}')
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
    log_admin_action('user_revoke', target_type='user', target_id=str(user.id), detail=f'撤销 {user.username}')
    db.session.commit()
    return jsonify({'status': 'ok', 'message': f'已取消用户 {user.username} 的使用权限'})


@auth_bp.route('/api/admin/all-users', methods=['GET'])
@login_required
@admin_required
def list_all_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({
        'users': [user_info(u) for u in users if not u.is_admin],
        'administrators': [user_info(u) for u in users if u.is_admin],
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
            'total': User.query.filter_by(is_admin=False).count(),
            'administrator_count': User.query.filter_by(is_admin=True).count(),
            'approved': User.query.filter_by(is_approved=True, is_admin=False).count(),
            'pending': User.query.filter_by(approval_requested=True, is_approved=False, is_admin=False).count(),
            'personal_api': User.query.filter(User.llm_api_key.isnot(None), User.is_admin == False).count(),
            'quota_exhausted': User.query.filter(
                User.is_admin == False,
                User.is_approved == False,
                User.llm_api_key.is_(None),
                User.free_api_used >= free_api_limit(),
            ).count(),
        },
        'usage': {
            'total': AnalysisRecord.query.count(),
            'today': AnalysisRecord.query.filter(AnalysisRecord.created_at >= today).count(),
            'last_7_days': AnalysisRecord.query.filter(AnalysisRecord.created_at >= week_start).count(),
            'by_module': {module or 'unknown': count for module, count in module_rows},
            'recent_by_module': {module or 'unknown': count for module, count in recent_module_rows},
        },
    })
