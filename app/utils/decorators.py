from functools import wraps
from flask import jsonify
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': {'code': 'UNAUTHORIZED', 'message': 'Authentication required.'}
            }), 401
        if current_user.role != 'admin':
            return jsonify({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'Administrator access required.'}
            }), 403
        return f(*args, **kwargs)
    return decorated_function


def active_user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': {'code': 'UNAUTHORIZED', 'message': 'Authentication required.'}
            }), 401
        if not current_user.is_active:
            return jsonify({
                'success': False,
                'error': {'code': 'ACCOUNT_DISABLED', 'message': 'This account has been deactivated.'}
            }), 403
        return f(*args, **kwargs)
    return decorated_function
