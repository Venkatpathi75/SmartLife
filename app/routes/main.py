from flask import Blueprint, jsonify, render_template

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/login')
def login_page():
    return render_template('index.html')


@main_bp.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'success': True,
        'data': {
            'status': 'healthy',
            'application': 'SmartLife',
            'version': '1.0.0'
        },
        'message': 'SmartLife API is running successfully.'
    }), 200
