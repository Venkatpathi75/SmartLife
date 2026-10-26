from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.notification import Notification
from app.services.notification_service import NotificationService
from app.utils.decorators import active_user_required

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@notifications_bp.route('', methods=['GET'])
@login_required
@active_user_required
def get_notifications():
    # Automatically scan for up-to-date alerts
    NotificationService.sync_user_notifications(current_user.id)

    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(30)\
        .all()

    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

    return jsonify({
        'success': True,
        'data': {
            'notifications': [n.to_dict() for n in notifications],
            'unread_count': unread_count
        }
    }), 200


@notifications_bp.route('/<int:notification_id>/read', methods=['PATCH'])
@login_required
@active_user_required
def mark_read(notification_id):
    notif = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not notif:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Notification not found.'}}), 404

    notif.is_read = True
    db.session.commit()

    return jsonify({'success': True, 'data': notif.to_dict(), 'message': 'Marked as read.'}), 200


@notifications_bp.route('/read-all', methods=['POST'])
@login_required
@active_user_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()

    return jsonify({'success': True, 'message': 'All notifications marked as read.'}), 200


@notifications_bp.route('/<int:notification_id>', methods=['DELETE'])
@login_required
@active_user_required
def delete_notification(notification_id):
    notif = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not notif:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Notification not found.'}}), 404

    db.session.delete(notif)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Notification dismissed.'}), 200
