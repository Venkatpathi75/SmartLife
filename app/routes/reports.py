from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.task import Task
from app.models.transaction import Transaction, Category
from app.utils.decorators import active_user_required

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')


def parse_date(date_str, fallback):
    if not date_str:
        return fallback
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return fallback


@reports_bp.route('/analytics', methods=['GET'])
@login_required
@active_user_required
def get_analytics():
    today = date.today()
    first_of_month = date(today.year, today.month, 1)

    start_date = parse_date(request.args.get('start_date'), first_of_month)
    end_date = parse_date(request.args.get('end_date'), today)

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    now_utc = datetime.now(timezone.utc)

    # 1. Task Metrics
    total_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.created_at >= start_dt,
        Task.created_at <= end_dt
    ).count()

    completed_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.status == 'completed',
        Task.completed_at >= start_dt,
        Task.completed_at <= end_dt
    ).count()

    pending_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.status.in_(['pending', 'in_progress'])
    ).count()

    overdue_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.status != 'completed',
        Task.due_date < now_utc
    ).count()

    completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0

    # 2. Financial Metrics (Exact Decimal Arithmetic)
    inc_query = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'income',
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date
    ).scalar()
    total_income = Decimal(str(inc_query))

    exp_query = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date
    ).scalar()
    total_expense = Decimal(str(exp_query))

    net_cash_flow = total_income - total_expense
    savings_rate = round(float((net_cash_flow / total_income) * 100), 1) if total_income > Decimal('0.00') else 0.0

    # 3. Spending Breakdown by Category
    cat_breakdown = db.session.query(
        func.coalesce(Category.name, 'Uncategorized').label('name'),
        func.coalesce(Category.icon, 'fa-receipt').label('icon'),
        func.coalesce(Category.color, '#64748b').label('color'),
        func.sum(Transaction.amount).label('total_amount'),
        func.count(Transaction.id).label('tx_count')
    ).outerjoin(Category, Transaction.category_id == Category.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date
    ).group_by(Category.name, Category.icon, Category.color).order_by(func.sum(Transaction.amount).desc()).all()

    category_results = []
    for c in cat_breakdown:
        amt = Decimal(str(c.total_amount))
        pct = round(float((amt / total_expense) * 100), 1) if total_expense > Decimal('0.00') else 0.0
        category_results.append({
            'name': c.name,
            'icon': c.icon,
            'color': c.color,
            'amount': float(amt),
            'count': c.tx_count,
            'percentage': pct
        })

    return jsonify({
        'success': True,
        'data': {
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            },
            'tasks': {
                'total': total_tasks,
                'completed': completed_tasks,
                'pending': pending_tasks,
                'overdue': overdue_tasks,
                'completion_rate': completion_rate
            },
            'finances': {
                'total_income': float(total_income),
                'total_expense': float(total_expense),
                'net_cash_flow': float(net_cash_flow),
                'savings_rate': savings_rate
            },
            'categories': category_results
        }
    }), 200
