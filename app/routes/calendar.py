from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.task import Task
from app.models.transaction import Transaction
from app.utils.decorators import active_user_required

calendar_bp = Blueprint('calendar', __name__, url_prefix='/api/calendar')


def parse_iso(dt_str):
    if not dt_str:
        return None
    try:
        clean = dt_str.replace('Z', '+00:00')
        return datetime.fromisoformat(clean)
    except (ValueError, TypeError):
        return None


@calendar_bp.route('/events', methods=['GET'])
@login_required
@active_user_required
def get_calendar_events():
    """
    Returns FullCalendar-compatible events (tasks & transactions) 
    between 'start' and 'end' dates for the authenticated user.
    """
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    show_tasks = request.args.get('show_tasks', 'true').lower() == 'true'
    show_finances = request.args.get('show_finances', 'true').lower() == 'true'

    start_dt = parse_iso(start_str)
    end_dt = parse_iso(end_str)

    events = []
    currency_symbol = '₹' if current_user.currency == 'INR' else '$'

    # 1. Collect Tasks
    if show_tasks:
        task_query = Task.query.filter_by(user_id=current_user.id)
        if start_dt and end_dt:
            task_query = task_query.filter(
                Task.due_date >= start_dt,
                Task.due_date <= end_dt
            )
        
        tasks = task_query.all()
        for t in tasks:
            if not t.due_date:
                continue

            # Color coding based on priority and completion
            if t.status == 'completed':
                bg_color = '#10b981' # emerald green
                border_color = '#059669'
            elif t.priority == 'urgent':
                bg_color = '#ef4444' # red
                border_color = '#dc2626'
            elif t.priority == 'high':
                bg_color = '#f59e0b' # amber
                border_color = '#d97706'
            elif t.priority == 'low':
                bg_color = '#64748b' # slate
                border_color = '#475569'
            else:
                bg_color = '#4f46e5' # indigo (medium)
                border_color = '#4338ca'

            events.append({
                'id': f'task_{t.id}',
                'taskId': t.id,
                'title': f"{'✓ ' if t.status == 'completed' else ''}{t.title}",
                'start': t.due_date.isoformat(),
                'allDay': False,
                'backgroundColor': bg_color,
                'borderColor': border_color,
                'textColor': '#ffffff',
                'extendedProps': {
                    'eventType': 'task',
                    'priority': t.priority,
                    'status': t.status,
                    'description': t.description or ''
                }
            })

    # 2. Collect Financial Transactions
    if show_finances and start_dt and end_dt:
        tx_query = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= start_dt.date(),
            Transaction.transaction_date <= end_dt.date()
        ).all()

        for tx in tx_query:
            is_income = tx.type == 'income'
            bg_color = '#0d9488' if is_income else '#e11d48' # teal vs rose
            prefix = '+ ' if is_income else '- '

            events.append({
                'id': f'tx_{tx.id}',
                'txId': tx.id,
                'title': f"{prefix}{currency_symbol}{tx.amount:,.0f} {tx.title}",
                'start': tx.transaction_date.isoformat(),
                'allDay': True,
                'backgroundColor': bg_color,
                'borderColor': bg_color,
                'textColor': '#ffffff',
                'extendedProps': {
                    'eventType': 'transaction',
                    'txType': tx.type,
                    'amount': float(tx.amount),
                    'category': tx.category.name if tx.category else 'General'
                }
            })

    return jsonify({'success': True, 'data': events}), 200


@calendar_bp.route('/events/<int:task_id>/reschedule', methods=['PATCH'])
@login_required
@active_user_required
def reschedule_task(task_id):
    """Updates task due date after a calendar drag-and-drop or resize operation."""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Task not found.'}}), 404

    data = request.get_json(silent=True) or {}
    new_date_str = data.get('new_date')

    if not new_date_str:
        return jsonify({'success': False, 'error': {'code': 'INVALID_DATE', 'message': 'New date is required.'}}), 400

    new_date = parse_iso(new_date_str)
    if not new_date:
        return jsonify({'success': False, 'error': {'code': 'INVALID_FORMAT', 'message': 'Invalid date format.'}}), 400

    task.due_date = new_date
    db.session.commit()

    return jsonify({
        'success': True,
        'data': task.to_dict(),
        'message': f"Task rescheduled to {new_date.strftime('%b %d, %Y %I:%M %p')}."
    }), 200
