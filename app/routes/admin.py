from datetime import datetime, timezone
from decimal import Decimal
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.user import User
from app.models.task import Task
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.notification import AuditLog
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def log_admin_action(action, target_type, target_id, details=None):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    log = AuditLog(
        actor_id=current_user.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip,
        details=details
    )
    db.session.add(log)
    db.session.commit()


@admin_bp.route('/stats', methods=['GET'])
@login_required
@admin_required
def get_admin_stats():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active_account=True).count()
    inactive_users = total_users - active_users
    admin_users = User.query.filter_by(role='admin').count()

    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(status='completed').count()

    total_transactions = Transaction.query.count()
    total_volume_query = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).scalar()
    total_volume = float(Decimal(str(total_volume_query)))

    total_budgets = Budget.query.count()
    total_audit_events = AuditLog.query.count()

    return jsonify({
        'success': True,
        'data': {
            'users': {
                'total': total_users,
                'active': active_users,
                'inactive': inactive_users,
                'admins': admin_users
            },
            'tasks': {
                'total': total_tasks,
                'completed': completed_tasks
            },
            'finances': {
                'total_transactions': total_transactions,
                'total_volume': total_volume,
                'total_budgets': total_budgets
            },
            'audit_events_count': total_audit_events
        }
    }), 200


@admin_bp.route('/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    search = request.args.get('search', '').strip().lower()
    status_filter = request.args.get('status', 'all')
    role_filter = request.args.get('role', 'all')

    query = User.query

    if search:
        query = query.filter(User.name.ilike(f'%{search}%') | User.email.ilike(f'%{search}%'))

    if status_filter == 'active':
        query = query.filter_by(is_active_account=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active_account=False)

    if role_filter in ['admin', 'user']:
        query = query.filter_by(role=role_filter)

    users = query.order_by(User.created_at.desc()).all()

    user_list = []
    for u in users:
        task_count = Task.query.filter_by(user_id=u.id).count()
        tx_count = Transaction.query.filter_by(user_id=u.id).count()

        user_list.append({
            'id': u.id,
            'name': u.name,
            'email': u.email,
            'role': u.role,
            'is_active': u.is_active_account,
            'currency': u.currency,
            'created_at': u.created_at.strftime('%Y-%m-%d %H:%M') if u.created_at else None,
            'task_count': task_count,
            'transaction_count': tx_count
        })

    return jsonify({'success': True, 'data': user_list}), 200


@admin_bp.route('/users/<int:user_id>/status', methods=['PATCH'])
@login_required
@admin_required
def toggle_user_status(user_id):
    if user_id == current_user.id:
        return jsonify({
            'success': False,
            'error': {'code': 'SELF_LOCKOUT_FORBIDDEN', 'message': 'You cannot deactivate your own administrator account.'}
        }), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'User not found.'}}), 404

    user.is_active_account = not user.is_active_account
    new_state = 'Activated' if user.is_active_account else 'Deactivated'
    db.session.commit()

    log_admin_action(
        action=f"USER_STATUS_{new_state.upper()}",
        target_type="user",
        target_id=user.id,
        details=f"Admin {current_user.email} changed account status of {user.email} to {new_state}."
    )

    return jsonify({
        'success': True,
        'data': {
            'user_id': user.id,
            'is_active': user.is_active_account
        },
        'message': f'User account {user.email} has been {new_state.lower()} successfully.'
    }), 200


@admin_bp.route('/audit-logs', methods=['GET'])
@login_required
@admin_required
def get_audit_logs():
    logs = db.session.query(
        AuditLog,
        User.name.label('actor_name'),
        User.email.label('actor_email')
    ).outerjoin(User, AuditLog.actor_id == User.id)\
     .order_by(AuditLog.created_at.desc())\
     .limit(50)\
     .all()

    audit_records = []
    for log, actor_name, actor_email in logs:
        audit_records.append({
            'id': log.id,
            'actor_name': actor_name or 'System',
            'actor_email': actor_email or 'system@internal',
            'action': log.action,
            'target_type': log.target_type,
            'target_id': log.target_id,
            'ip_address': log.ip_address,
            'details': log.details,
            'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else None
        })

    return jsonify({'success': True, 'data': audit_records}), 200
