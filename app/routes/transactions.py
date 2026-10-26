import csv
import io
from datetime import datetime, date, timezone
from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify, Response
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.transaction import Transaction, Category
from app.utils.decorators import active_user_required

transactions_bp = Blueprint('transactions', __name__, url_prefix='/api/transactions')

DEFAULT_EXPENSE_CATEGORIES = [
    ('Food & Dining', 'fa-utensils', '#ef4444'),
    ('Transportation', 'fa-car', '#f59e0b'),
    ('Education', 'fa-graduation-cap', '#3b82f6'),
    ('Shopping', 'fa-bag-shopping', '#ec4899'),
    ('Entertainment', 'fa-film', '#8b5cf6'),
    ('Healthcare', 'fa-heart-pulse', '#10b981'),
    ('Bills & Utilities', 'fa-bolt', '#eab308'),
    ('Rent & Housing', 'fa-house', '#6366f1'),
    ('Travel', 'fa-plane', '#06b6d4'),
    ('Personal Care', 'fa-spa', '#14b8a6'),
    ('Other Expense', 'fa-ellipsis', '#64748b'),
]

DEFAULT_INCOME_CATEGORIES = [
    ('Salary', 'fa-money-bill-wave', '#10b981'),
    ('Freelancing', 'fa-laptop-code', '#0ea5e9'),
    ('Business', 'fa-briefcase', '#6366f1'),
    ('Investments', 'fa-chart-line', '#8b5cf6'),
    ('Gifts & Grants', 'fa-gift', '#f43f5e'),
    ('Other Income', 'fa-circle-dollar-to-slot', '#64748b'),
]


def ensure_default_categories():
    """Seeds global default categories if they do not exist yet."""
    existing_count = Category.query.filter_by(user_id=None).count()
    if existing_count == 0:
        for name, icon, color in DEFAULT_EXPENSE_CATEGORIES:
            db.session.add(Category(user_id=None, name=name, type='expense', icon=icon, color=color))
        for name, icon, color in DEFAULT_INCOME_CATEGORIES:
            db.session.add(Category(user_id=None, name=name, type='income', icon=icon, color=color))
        db.session.commit()


def parse_date(date_str):
    if not date_str:
        return date.today()
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return date.today()


def parse_decimal_amount(amount_val):
    try:
        dec = Decimal(str(amount_val).strip())
        if dec <= Decimal('0.00'):
            return None
        return dec.quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        return None


@transactions_bp.route('/categories', methods=['GET'])
@login_required
@active_user_required
def get_categories():
    ensure_default_categories()
    cat_type = request.args.get('type')  # 'expense', 'income', or None

    query = Category.query.filter(
        (Category.user_id == None) | (Category.user_id == current_user.id)
    )
    if cat_type and cat_type in ['expense', 'income']:
        query = query.filter((Category.type == cat_type) | (Category.type == 'both'))

    categories = query.order_by(Category.name.asc()).all()
    return jsonify({
        'success': True,
        'data': [c.to_dict() for c in categories]
    }), 200


@transactions_bp.route('/categories', methods=['POST'])
@login_required
@active_user_required
def create_category():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    cat_type = data.get('type', 'expense')
    icon = data.get('icon', 'fa-tag').strip()
    color = data.get('color', '#4f46e5').strip()

    if not name:
        return jsonify({'success': False, 'error': {'code': 'INVALID_NAME', 'message': 'Category name is required.'}}), 400

    if cat_type not in ['expense', 'income', 'both']:
        return jsonify({'success': False, 'error': {'code': 'INVALID_TYPE', 'message': 'Type must be expense, income, or both.'}}), 400

    category = Category(
        user_id=current_user.id,
        name=name,
        type=cat_type,
        icon=icon,
        color=color
    )
    db.session.add(category)
    db.session.commit()

    return jsonify({
        'success': True,
        'data': category.to_dict(),
        'message': 'Category created successfully.'
    }), 201


@transactions_bp.route('', methods=['GET'])
@login_required
@active_user_required
def get_transactions():
    tx_type = request.args.get('type')  # 'income', 'expense', or 'all'
    category_id = request.args.get('category_id')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    search = request.args.get('search', '').strip().lower()
    sort_by = request.args.get('sort_by', 'date_desc')

    query = Transaction.query.filter_by(user_id=current_user.id)

    if tx_type and tx_type in ['income', 'expense']:
        query = query.filter(Transaction.type == tx_type)

    if category_id and category_id.isdigit():
        query = query.filter(Transaction.category_id == int(category_id))

    if start_date_str:
        query = query.filter(Transaction.transaction_date >= parse_date(start_date_str))

    if end_date_str:
        query = query.filter(Transaction.transaction_date <= parse_date(end_date_str))

    if search:
        query = query.filter(
            Transaction.title.ilike(f'%{search}%') |
            Transaction.merchant.ilike(f'%{search}%') |
            Transaction.notes.ilike(f'%{search}%')
        )

    if sort_by == 'date_asc':
        query = query.order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
    elif sort_by == 'amount_desc':
        query = query.order_by(Transaction.amount.desc())
    elif sort_by == 'amount_asc':
        query = query.order_by(Transaction.amount.asc())
    else:
        query = query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())

    transactions = query.all()

    # Calculate filtered summary metrics using Decimal
    tot_inc = Decimal('0.00')
    tot_exp = Decimal('0.00')
    for tx in transactions:
        if tx.type == 'income':
            tot_inc += Decimal(str(tx.amount))
        else:
            tot_exp += Decimal(str(tx.amount))

    net_flow = tot_inc - tot_exp

    return jsonify({
        'success': True,
        'data': [tx.to_dict() for tx in transactions],
        'summary': {
            'total_income': float(tot_inc),
            'total_expense': float(tot_exp),
            'net_cash_flow': float(net_flow),
            'count': len(transactions)
        }
    }), 200


@transactions_bp.route('', methods=['POST'])
@login_required
@active_user_required
def create_transaction():
    data = request.get_json(silent=True) or {}
    title = data.get('title', '').strip()
    tx_type = data.get('type', 'expense')
    amount = parse_decimal_amount(data.get('amount'))
    tx_date = parse_date(data.get('transaction_date'))
    category_id = data.get('category_id')
    payment_method = data.get('payment_method', 'UPI / Cash').strip()
    merchant = data.get('merchant', '').strip()
    notes = data.get('notes', '').strip()

    if not title:
        return jsonify({'success': False, 'error': {'code': 'INVALID_TITLE', 'message': 'Transaction title is required.'}}), 400

    if tx_type not in ['income', 'expense']:
        return jsonify({'success': False, 'error': {'code': 'INVALID_TYPE', 'message': 'Type must be income or expense.'}}), 400

    if amount is None:
        return jsonify({'success': False, 'error': {'code': 'INVALID_AMOUNT', 'message': 'Amount must be a positive number greater than 0.'}}), 400

    if category_id:
        try:
            category_id = int(category_id)
        except (ValueError, TypeError):
            category_id = None

    tx = Transaction(
        user_id=current_user.id,
        category_id=category_id,
        title=title,
        amount=amount,
        type=tx_type,
        transaction_date=tx_date,
        payment_method=payment_method or 'UPI / Cash',
        merchant=merchant or None,
        notes=notes or None
    )

    db.session.add(tx)
    db.session.commit()

    return jsonify({
        'success': True,
        'data': tx.to_dict(),
        'message': f'{tx_type.capitalize()} recorded successfully.'
    }), 201


@transactions_bp.route('/<int:tx_id>', methods=['GET'])
@login_required
@active_user_required
def get_transaction(tx_id):
    tx = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first()
    if not tx:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Transaction not found.'}}), 404

    return jsonify({'success': True, 'data': tx.to_dict()}), 200


@transactions_bp.route('/<int:tx_id>', methods=['PUT'])
@login_required
@active_user_required
def update_transaction(tx_id):
    tx = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first()
    if not tx:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Transaction not found.'}}), 404

    data = request.get_json(silent=True) or {}
    if 'title' in data and data['title'].strip():
        tx.title = data['title'].strip()
    if 'amount' in data:
        amount = parse_decimal_amount(data['amount'])
        if amount is None:
            return jsonify({'success': False, 'error': {'code': 'INVALID_AMOUNT', 'message': 'Amount must be greater than 0.'}}), 400
        tx.amount = amount
    if 'type' in data and data['type'] in ['income', 'expense']:
        tx.type = data['type']
    if 'transaction_date' in data:
        tx.transaction_date = parse_date(data['transaction_date'])
    if 'category_id' in data:
        try:
            tx.category_id = int(data['category_id']) if data['category_id'] else None
        except (ValueError, TypeError):
            tx.category_id = None
    if 'payment_method' in data:
        tx.payment_method = data['payment_method'].strip() or 'UPI / Cash'
    if 'merchant' in data:
        tx.merchant = data['merchant'].strip() or None
    if 'notes' in data:
        tx.notes = data['notes'].strip() or None

    db.session.commit()

    return jsonify({
        'success': True,
        'data': tx.to_dict(),
        'message': 'Transaction updated successfully.'
    }), 200


@transactions_bp.route('/<int:tx_id>', methods=['DELETE'])
@login_required
@active_user_required
def delete_transaction(tx_id):
    tx = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first()
    if not tx:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Transaction not found.'}}), 404

    db.session.delete(tx)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Transaction deleted successfully.'}), 200


@transactions_bp.route('/export/csv', methods=['GET'])
@login_required
@active_user_required
def export_csv():
    """Generates and streams a CSV of the user's filtered transactions."""
    tx_type = request.args.get('type')
    category_id = request.args.get('category_id')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    query = Transaction.query.filter_by(user_id=current_user.id)
    if tx_type and tx_type in ['income', 'expense']:
        query = query.filter(Transaction.type == tx_type)
    if category_id and category_id.isdigit():
        query = query.filter(Transaction.category_id == int(category_id))
    if start_date_str:
        query = query.filter(Transaction.transaction_date >= parse_date(start_date_str))
    if end_date_str:
        query = query.filter(Transaction.transaction_date <= parse_date(end_date_str))

    transactions = query.order_by(Transaction.transaction_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Title', 'Type', 'Category', f'Amount ({current_user.currency})', 'Payment Method', 'Merchant/Source', 'Notes'])

    for t in transactions:
        writer.writerow([
            t.transaction_date.strftime('%Y-%m-%d'),
            t.title,
            t.type.capitalize(),
            t.category.name if t.category else 'General',
            f"{t.amount:.2f}",
            t.payment_method,
            t.merchant or '',
            t.notes or ''
        ])

    csv_data = output.getvalue()
    filename = f"smartlife_transactions_{date.today().strftime('%Y%m%d')}.csv"

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
