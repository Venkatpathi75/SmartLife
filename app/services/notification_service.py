from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from sqlalchemy import func
from app import db
from app.models.task import Task
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.notification import Notification


class NotificationService:
    @staticmethod
    def sync_user_notifications(user_id):
        """
        Scans tasks and active budgets to generate actionable in-app notifications.
        Avoids duplicate entries by verifying existing unread or recent notifications.
        """
        now_utc = datetime.now(timezone.utc)
        today = date.today()
        tomorrow_utc = now_utc + timedelta(days=1)

        # 1. Check for Tasks Due Soon (Due within 24 hours, not completed)
        due_soon_tasks = Task.query.filter(
            Task.user_id == user_id,
            Task.status.in_(['pending', 'in_progress']),
            Task.due_date > now_utc,
            Task.due_date <= tomorrow_utc
        ).all()

        for t in due_soon_tasks:
            # Check if notification already exists for this task
            existing = Notification.query.filter(
                Notification.user_id == user_id,
                Notification.type == 'task_due_soon',
                Notification.message.like(f'%"{t.title}"%')
            ).first()

            if not existing:
                due_time = t.due_date.strftime('%I:%M %p')
                n = Notification(
                    user_id=user_id,
                    title="Task Due Soon",
                    message=f'Task "{t.title}" is due today at {due_time}.',
                    type="task_due_soon"
                )
                db.session.add(n)

        # 2. Check for Overdue Tasks
        overdue_tasks = Task.query.filter(
            Task.user_id == user_id,
            Task.status.in_(['pending', 'in_progress']),
            Task.due_date < now_utc
        ).all()

        for t in overdue_tasks:
            existing = Notification.query.filter(
                Notification.user_id == user_id,
                Notification.type == 'task_overdue',
                Notification.message.like(f'%"{t.title}"%')
            ).first()

            if not existing:
                n = Notification(
                    user_id=user_id,
                    title="Task Overdue",
                    message=f'Task "{t.title}" was due on {t.due_date.strftime("%b %d")} and is currently overdue.',
                    type="task_overdue"
                )
                db.session.add(n)

        # 3. Check Active Budgets for Threshold Alerts
        active_budgets = Budget.query.filter(
            Budget.user_id == user_id,
            Budget.start_date <= today,
            Budget.end_date >= today
        ).all()

        for b in active_budgets:
            spent_query = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
                Transaction.user_id == user_id,
                Transaction.type == 'expense',
                Transaction.transaction_date >= b.start_date,
                Transaction.transaction_date <= b.end_date
            ).scalar()
            total_spent = Decimal(str(spent_query))
            budget_limit = Decimal(str(b.amount))

            if budget_limit > 0:
                pct = (total_spent / budget_limit) * 100

                if pct >= 100:
                    existing = Notification.query.filter(
                        Notification.user_id == user_id,
                        Notification.type == 'budget_exceeded',
                        Notification.message.like(f'%"{b.name}"%')
                    ).first()

                    if not existing:
                        n = Notification(
                            user_id=user_id,
                            title="Budget Exceeded",
                            message=f'Your budget "{b.name}" has exceeded its limit ({pct:.1f}% consumed).',
                            type="budget_exceeded"
                        )
                        db.session.add(n)

                elif pct >= 75:
                    existing = Notification.query.filter(
                        Notification.user_id == user_id,
                        Notification.type == 'budget_warning',
                        Notification.message.like(f'%"{b.name}"%')
                    ).first()

                    if not existing:
                        n = Notification(
                            user_id=user_id,
                            title="Budget Warning",
                            message=f'You have used {pct:.1f}% of your planned budget for "{b.name}".',
                            type="budget_warning"
                        )
                        db.session.add(n)

        db.session.commit()
