import os
from flask import Flask, jsonify, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = 'main.index'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        """Returns JSON 401 for API endpoints instead of redirecting to HTML."""
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': {'code': 'UNAUTHORIZED', 'message': 'Authentication required.'}
            }), 401
        return redirect(url_for('main.index'))

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.tasks import tasks_bp
    from app.routes.calendar import calendar_bp
    from app.routes.transactions import transactions_bp
    from app.routes.budgets import budgets_bp
    from app.routes.notifications import notifications_bp
    from app.routes.reports import reports_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)

    register_error_handlers(app)

    return app


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': {'code': 'BAD_REQUEST', 'message': str(error.description or 'Bad Request')}
        }), 400

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'error': {'code': 'FORBIDDEN', 'message': 'You do not have permission to access this resource.'}
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': 'The requested resource was not found.'}
        }), 404

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            'success': False,
            'error': {'code': 'RATE_LIMIT_EXCEEDED', 'message': f'Rate limit exceeded: {e.description}'}
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': {'code': 'INTERNAL_SERVER_ERROR', 'message': 'An unexpected server error occurred.'}
        }), 500
