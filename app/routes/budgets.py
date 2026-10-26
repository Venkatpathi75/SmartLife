from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.budget import Budget, BudgetCategory
from app.models.transaction import Transaction, Category
from app.utils.decorators import active_user_required

budgets_bp = Blueprint('budgets', __name__, url_prefix='/api/budgets')


def parse_date(date_str, fallback=None):
    if not date_str:
        return fallback or date.today()
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return fallback or date.today()


def parse_decimal_amount(amount_val):
    try:
        dec = Decimal(str(amount_val).strip())
        if dec <= Decimal('0.00'):
            return None
        return dec.quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        return None


@budgets_bp.route('', methods=['GET'])
@login_required
@active_user_required
def get_budgets():
    budgets = Budget.query.filter_by(user_id=current_user.id).order_by(Budget.start_date.desc()).all()
    today = date.today()
    results = []

    for b in budgets:
        # Calculate actual total expenses within the budget date window
        total_spent_query = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'expense',
            Transaction.transaction_date >= b.start_date,
            Transaction.transaction_date <= b.end_date
        ).scalar()
        total_spent = Decimal(str(total_spent_query))

        limit_amount = Decimal(str(b.amount))
        remaining = limit_amount - total_spent
        percent_used = round(float((total_spent / limit_amount) * 100), 1) if limit_amount > 0 else 0.0

        is_active = (b.start_date <= today <= b.end_date)

        # Status threshold
        if percent_used >= 100.0:
            status = 'exceeded'
        elif percent_used >= 75.0:
            status = 'warning'
        else:
            status = 'safe'

        # Category breakdowns
        category_stats = []
        for bc in b.categories:
            cat_spent_query = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
                Transaction.user_id == current_user.id,
                Transaction.category_id == bc.category_id,
                Transaction.type == 'expense',
                Transaction.transaction_date >= b.start_date,
                Transaction.transaction_date <= b.end_date
            ).scalar()
            cat_spent = Decimal(str(cat_spent_query))
            cat_limit = Decimal(str(bc.limit_amount))
            cat_pct = round(float((cat_spent / cat_limit) * 100), 1) if cat_limit > 0 else 0.0

            category_stats.append({
                'category_id': bc.category_id,
                'category_name': bc.category.name if bc.category else 'General',
                'category_icon': bc.category.icon if bc.category else 'fa-tag',
                'category_color': bc.category.color if bc.category else '#64748b',
                'limit_amount': float(cat_limit),
                'spent': float(cat_spent),
                'remaining': float(cat_limit - cat_spent),
                'percent_used': cat_pct,
                'is_exceeded': cat_spent > cat_limit
            })

        results.append({
            'id': b.id,
            'name': b.name,
            'amount': float(limit_amount),
            'period': b.period,
            'start_date': b.start_date.isoformat(),
            'end_date': b.end_date.isoformat(),
            'is_active': is_active,
            'spent': float(total_spent),
            'remaining': float(remaining),
            'percent_used': percent_used,
            'status': status,
            'categories': category_stats
        })

    return jsonify({'success': True, 'data': results}), 200


@budgets_bp.route('', methods=['POST'])
@login_required
@active_user_required
def create_budget():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    amount = parse_decimal_amount(data.get('amount'))
    period = data.get('period', 'monthly')
    start_date = parse_date(data.get('start_date'))
    
    # End date calculation: fallback to end of the month
    if data.get('end_date'):
        end_date = parse_date(data.get('end_date'))
    else:
        # Default to month end
        next_month = start_date.replace(day=28) + timedelta(days=4)
        end_date = next_month - timedelta(days=next_month.day)

    if not name:
        return jsonify({'success': False, 'error': {'code': 'INVALID_NAME', 'message': 'Budget name is required.'}}), 400

    if amount is None:
        return jsonify({'success': False, 'error': {'code': 'INVALID_AMOUNT', 'message': 'Budget amount must be a positive number.'}}), 400

    if start_date > end_date:
        return jsonify({'success': False, 'error': {'code': 'INVALID_DATES', 'message': 'Start date cannot be after end date.'}}), 400

    budget = Budget(
        user_id=current_user.id,
        name=name,
        amount=amount,
        period=period,
        start_date=start_date,
        end_date=end_date
    )
    db.session.add(budget)
    db.session.flush()

    # Category limit allocations
    category_limits = data.get('category_limits', [])
    for cl in category_limits:
        cat_id = cl.get('category_id')
        cat_amount = parse_decimal_amount(cl.get('limit_amount'))
        if cat_id and cat_amount:
            bc = BudgetCategory(budget_id=budget.id, category_id=int(cat_id), limit_amount=cat_amount)
            db.session.add(bc)

    db.session.commit()

    return jsonify({
        'success': True,
        'data': budget.to_dict(),
        'message': 'Budget plan created successfully.'
    }), 201


@budgets_bp.route('/<int:budget_id>', methods=['GET'])
@login_required
@active_user_required
def get_budget(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first()
    if not budget:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Budget not found.'}}), 404

    return jsonify({'success': True, 'data': budget.to_dict()}), 200


@budgets_bp.route('/<int:budget_id>', methods=['PUT'])
@login_required
@active_user_required
def update_budget(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first()
    if not budget:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Budget not found.'}}), 404

    data = request.get_json(silent=True) or {}
    if 'name' in data and data['name'].strip():
        budget.name = data['name'].strip()
    if 'amount' in data:
        amount = parse_decimal_amount(data['amount'])
        if amount is None:
            return jsonify({'success': False, 'error': {'code': 'INVALID_AMOUNT', 'message': 'Amount must be greater than 0.'}}), 400
        budget.amount = amount
    if 'period' in data:
        budget.period = data['period']
    if 'start_date' in data:
        budget.start_date = parse_date(data['start_date'])
    if 'end_date' in data:
        budget.end_date = parse_date(data['end_date'])

    # Update category limits if provided
    if 'category_limits' in data:
        BudgetCategory.query.filter_by(budget_id=budget.id).delete()
        for cl in data['category_limits']:
            cat_id = cl.get('category_id')
            cat_amount = parse_decimal_amount(cl.get('limit_amount'))
            if cat_id and cat_amount:
                bc = BudgetCategory(budget_id=budget.id, category_id=int(cat_id), limit_amount=cat_amount)
                db.session.add(bc)

    db.session.commit()

    return jsonify({
        'success': True,
        'data': budget.to_dict(),
        'message': 'Budget updated successfully.'
    }), 200


@budgets_bp.route('/<int:budget_id>', methods=['DELETE'])
@login_required
@active_user_required
def delete_budget(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first()
    if not budget:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Budget not found.'}}), 404

    db.session.delete(budget)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Budget deleted successfully.'}), 200
