import re
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from flask_wtf.csrf import generate_csrf
from app import db, limiter
from app.models.user import User
from app.utils.decorators import active_user_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'


@auth_bp.route('/csrf-token', methods=['GET'])
def get_csrf_token():
    """Returns a fresh CSRF token for API clients."""
    token = generate_csrf()
    return jsonify({
        'success': True,
        'data': {'csrf_token': token}
    }), 200


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not name or len(name) < 2:
        return jsonify({'success': False, 'error': {'code': 'INVALID_NAME', 'message': 'Name must be at least 2 characters.'}}), 400

    if not email or not re.match(EMAIL_REGEX, email):
        return jsonify({'success': False, 'error': {'code': 'INVALID_EMAIL', 'message': 'A valid email address is required.'}}), 400

    if not password or len(password) < 8:
        return jsonify({'success': False, 'error': {'code': 'INVALID_PASSWORD', 'message': 'Password must be at least 8 characters long.'}}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': {'code': 'EMAIL_EXISTS', 'message': 'An account with this email already exists.'}}), 409

    user = User(
        name=name,
        email=email,
        role='user',  # Security: regular registration cannot grant admin privileges
        currency=data.get('currency', 'INR')
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'success': True,
        'data': {'user': user.to_dict()},
        'message': 'Registration successful. You can now log in.'
    }), 201


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    remember = bool(data.get('remember', False))

    if not email or not password:
        return jsonify({'success': False, 'error': {'code': 'MISSING_FIELDS', 'message': 'Email and password are required.'}}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'success': False, 'error': {'code': 'INVALID_CREDENTIALS', 'message': 'Invalid email or password.'}}), 401

    if not user.is_active:
        return jsonify({'success': False, 'error': {'code': 'ACCOUNT_DISABLED', 'message': 'Your account has been deactivated.'}}), 403

    login_user(user, remember=remember)

    return jsonify({
        'success': True,
        'data': {'user': user.to_dict()},
        'message': f'Welcome back, {user.name}!'
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully.'
    }), 200


@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    if not current_user.is_authenticated:
        return jsonify({
            'success': True,
            'data': {'authenticated': False, 'user': None}
        }), 200

    return jsonify({
        'success': True,
        'data': {
            'authenticated': True,
            'user': current_user.to_dict()
        }
    }), 200


@auth_bp.route('/profile', methods=['PUT'])
@login_required
@active_user_required
def update_profile():
    data = request.get_json(silent=True) or {}
    
    if 'name' in data and len(data['name'].strip()) >= 2:
        current_user.name = data['name'].strip()
    if 'currency' in data and data['currency'].strip():
        current_user.currency = data['currency'].strip().upper()
    if 'theme' in data and data['theme'] in ['light', 'dark']:
        current_user.theme = data['theme']
    if 'timezone' in data and data['timezone'].strip():
        current_user.timezone = data['timezone'].strip()

    db.session.commit()

    return jsonify({
        'success': True,
        'data': {'user': current_user.to_dict()},
        'message': 'Profile updated successfully.'
    }), 200


@auth_bp.route('/password', methods=['PUT'])
@login_required
@active_user_required
def change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_user.check_password(current_password):
        return jsonify({'success': False, 'error': {'code': 'INCORRECT_PASSWORD', 'message': 'Incorrect current password.'}}), 400

    if not new_password or len(new_password) < 8:
        return jsonify({'success': False, 'error': {'code': 'WEAK_PASSWORD', 'message': 'New password must be at least 8 characters long.'}}), 400

    current_user.set_password(new_password)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Password changed successfully.'
    }), 200
