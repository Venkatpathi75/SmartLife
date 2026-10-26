from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.utils.decorators import active_user_required
from app.services.stats_service import StatsService
from app.models.task import Task
from app.models.transaction import Transaction

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('/summary', methods=['GET'])
@login_required
@active_user_required
def get_summary():
    summary_data = StatsService.get_dashboard_summary(current_user.id)
    return jsonify({
        'success': True,
        'data': summary_data
    }), 200


@dashboard_bp.route('/charts', methods=['GET'])
@login_required
@active_user_required
def get_charts():
    charts_data = StatsService.get_dashboard_charts(current_user.id)
    return jsonify({
        'success': True,
        'data': charts_data
    }), 200


@dashboard_bp.route('/recent-activity', methods=['GET'])
@login_required
@active_user_required
def get_recent_activity():
    recent_tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).limit(5).all()
    recent_txs = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.transaction_date.desc()).limit(5).all()

    return jsonify({
        'success': True,
        'data': {
            'tasks': [t.to_dict() for t in recent_tasks],
            'transactions': [tx.to_dict() for tx in recent_txs]
        }
    }), 200
