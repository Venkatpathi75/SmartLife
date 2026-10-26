from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.task import Task, TaskChecklist
from app.models.transaction import Category
from app.utils.decorators import active_user_required

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')


def parse_datetime(dt_str):
    if not dt_str:
        return None
    try:
        # Handles both YYYY-MM-DDTHH:MM and ISO strings
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None


@tasks_bp.route('', methods=['GET'])
@login_required
@active_user_required
def get_tasks():
    status = request.args.get('status')
    priority = request.args.get('priority')
    category_id = request.args.get('category_id')
    search = request.args.get('search', '').strip().lower()
    sort_by = request.args.get('sort_by', 'due_date')  # due_date, priority, created_at
    filter_type = request.args.get('filter_type')       # today, upcoming, overdue, completed

    query = Task.query.filter_by(user_id=current_user.id)
    now_utc = datetime.now(timezone.utc)

    # Status filter
    if status and status != 'all':
        query = query.filter(Task.status == status)

    # Priority filter
    if priority and priority != 'all':
        query = query.filter(Task.priority == priority)

    # Category filter
    if category_id and category_id.isdigit():
        query = query.filter(Task.category_id == int(category_id))

    # Text search
    if search:
        query = query.filter(Task.title.ilike(f'%{search}%') | Task.description.ilike(f'%{search}%'))

    # Quick preset filter views
    today_start = datetime.combine(datetime.now().date(), datetime.min.time())
    today_end = datetime.combine(datetime.now().date(), datetime.max.time())

    if filter_type == 'today':
        query = query.filter(Task.due_date >= today_start, Task.due_date <= today_end)
    elif filter_type == 'upcoming':
        query = query.filter(Task.due_date > today_end, Task.status != 'completed')
    elif filter_type == 'overdue':
        query = query.filter(Task.due_date < now_utc, Task.status != 'completed')
    elif filter_type == 'completed':
        query = query.filter(Task.status == 'completed')

    # Sorting
    if sort_by == 'priority':
        query = query.order_by(Task.priority.desc(), Task.due_date.asc().nullslast())
    elif sort_by == 'created_at':
        query = query.order_by(Task.created_at.desc())
    else:
        query = query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())

    tasks = query.all()
    return jsonify({
        'success': True,
        'data': [task.to_dict() for task in tasks]
    }), 200


@tasks_bp.route('', methods=['POST'])
@login_required
@active_user_required
def create_task():
    data = request.get_json(silent=True) or {}
    title = data.get('title', '').strip()

    if not title:
        return jsonify({'success': False, 'error': {'code': 'INVALID_TITLE', 'message': 'Task title is required.'}}), 400

    task = Task(
        user_id=current_user.id,
        title=title,
        description=data.get('description', '').strip(),
        start_date=parse_datetime(data.get('start_date')),
        due_date=parse_datetime(data.get('due_date')),
        priority=data.get('priority', 'medium'),
        status=data.get('status', 'pending'),
        category_id=data.get('category_id') if data.get('category_id') else None,
        is_recurring=bool(data.get('is_recurring', False)),
        recurrence_interval=data.get('recurrence_interval')
    )

    db.session.add(task)
    db.session.flush()

    # Add optional checklist / subtask items
    checklists = data.get('checklists', [])
    for item_title in checklists:
        if isinstance(item_title, str) and item_title.strip():
            cl = TaskChecklist(task_id=task.id, title=item_title.strip())
            db.session.add(cl)

    db.session.commit()

    return jsonify({
        'success': True,
        'data': task.to_dict(),
        'message': 'Task created successfully.'
    }), 201


@tasks_bp.route('/<int:task_id>', methods=['GET'])
@login_required
@active_user_required
def get_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Task not found.'}}), 404

    return jsonify({'success': True, 'data': task.to_dict()}), 200


@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@login_required
@active_user_required
def update_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Task not found.'}}), 404

    data = request.get_json(silent=True) or {}
    if 'title' in data and data['title'].strip():
        task.title = data['title'].strip()
    if 'description' in data:
        task.description = data['description'].strip()
    if 'start_date' in data:
        task.start_date = parse_datetime(data.get('start_date'))
    if 'due_date' in data:
        task.due_date = parse_datetime(data.get('due_date'))
    if 'priority' in data:
        task.priority = data['priority']
    if 'status' in data:
        task.status = data['status']
        if task.status == 'completed' and not task.completed_at:
            task.completed_at = datetime.now(timezone.utc)
        elif task.status != 'completed':
            task.completed_at = None
    if 'category_id' in data:
        task.category_id = data['category_id'] if data['category_id'] else None

    # Replace checklist items if passed
    if 'checklists' in data:
        TaskChecklist.query.filter_by(task_id=task.id).delete()
        for item in data['checklists']:
            title = item.get('title', '').strip() if isinstance(item, dict) else str(item).strip()
            is_comp = item.get('is_completed', False) if isinstance(item, dict) else False
            if title:
                cl = TaskChecklist(task_id=task.id, title=title, is_completed=is_comp)
                db.session.add(cl)

    db.session.commit()
    return jsonify({'success': True, 'data': task.to_dict(), 'message': 'Task updated successfully.'}), 200


@tasks_bp.route('/<int:task_id>/status', methods=['PATCH'])
@login_required
@active_user_required
def toggle_task_status(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Task not found.'}}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get('status')

    if not new_status:
        # Default toggle logic between completed and pending
        new_status = 'pending' if task.status == 'completed' else 'completed'

    task.status = new_status
    if task.status == 'completed':
        task.completed_at = datetime.now(timezone.utc)
    else:
        task.completed_at = None

    db.session.commit()
    return jsonify({
        'success': True,
        'data': task.to_dict(),
        'message': f'Task marked as {task.status}.'
    }), 200


@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@login_required
@active_user_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Task not found.'}}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Task deleted successfully.'}), 200


@tasks_bp.route('/checklists/<int:item_id>/toggle', methods=['PATCH'])
@login_required
@active_user_required
def toggle_checklist(item_id):
    item = TaskChecklist.query.join(Task).filter(
        TaskChecklist.id == item_id,
        Task.user_id == current_user.id
    ).first()

    if not item:
        return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Checklist item not found.'}}), 404

    item.is_completed = not item.is_completed
    db.session.commit()
    return jsonify({'success': True, 'data': item.to_dict()}), 200
