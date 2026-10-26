from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from sqlalchemy import func
from app import db
from app.models.task import Task
from app.models.transaction import Transaction, Category
from app.models.budget import Budget


class StatsService:
    @staticmethod
    def get_dashboard_summary(user_id):
        now_utc = datetime.now(timezone.utc)
        today = date.today()
        first_of_month = date(today.year, today.month, 1)

        # 1. Task Metrics
        total_tasks = Task.query.filter_by(user_id=user_id).count()
        completed_tasks = Task.query.filter_by(user_id=user_id, status='completed').count()
        pending_tasks = Task.query.filter(
            Task.user_id == user_id,
            Task.status.in_(['pending', 'in_progress'])
        ).count()
        
        overdue_tasks = Task.query.filter(
            Task.user_id == user_id,
            Task.status != 'completed',
            Task.due_date < now_utc
        ).count()

        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        today_tasks = Task.query.filter(
            Task.user_id == user_id,
            Task.due_date >= today_start,
            Task.due_date <= today_end
        ).count()

        # 2. Financial Metrics (Current Month)
        income_query = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'income',
            Transaction.transaction_date >= first_of_month,
            Transaction.transaction_date <= today
        ).scalar()
        total_income = Decimal(str(income_query))

        expense_query = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.transaction_date >= first_of_month,
            Transaction.transaction_date <= today
        ).scalar()
        total_expense = Decimal(str(expense_query))

        net_savings = total_income - total_expense

        # 3. Active Budget Utilization
        active_budget = Budget.query.filter(
            Budget.user_id == user_id,
            Budget.start_date <= today,
            Budget.end_date >= today
        ).first()

        budget_limit = Decimal(str(active_budget.amount)) if active_budget else Decimal('0.00')
        remaining_budget = budget_limit - total_expense if active_budget else Decimal('0.00')
        budget_utilization_pct = round(float((total_expense / budget_limit) * 100), 1) if budget_limit > 0 else 0.0

        return {
            'tasks': {
                'total': total_tasks,
                'completed': completed_tasks,
                'pending': pending_tasks,
                'overdue': overdue_tasks,
                'today': today_tasks,
                'completion_rate': round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0
            },
            'finances': {
                'income': float(total_income),
                'expenses': float(total_expense),
                'savings': float(net_savings),
                'budget_limit': float(budget_limit),
                'remaining_budget': float(remaining_budget),
                'budget_utilization_pct': budget_utilization_pct,
                'has_active_budget': active_budget is not None
            }
        }

    @staticmethod
    def get_dashboard_charts(user_id):
        today = date.today()

        # A. Weekly Task Completion (Mon - Sun of current week)
        start_of_week = today - timedelta(days=today.weekday())
        week_days = [start_of_week + timedelta(days=i) for i in range(7)]
        week_labels = [d.strftime('%a') for d in week_days]
        completed_counts = []
        created_counts = []

        for d in week_days:
            d_start = datetime.combine(d, datetime.min.time())
            d_end = datetime.combine(d, datetime.max.time())
            
            c_count = Task.query.filter(
                Task.user_id == user_id,
                Task.status == 'completed',
                Task.completed_at >= d_start,
                Task.completed_at <= d_end
            ).count()
            completed_counts.append(c_count)

            cr_count = Task.query.filter(
                Task.user_id == user_id,
                Task.created_at >= d_start,
                Task.created_at <= d_end
            ).count()
            created_counts.append(cr_count)

        # B. Expense Breakdown by Category (Current Month)
        first_of_month = date(today.year, today.month, 1)
        cat_expenses = db.session.query(
            func.coalesce(Category.name, 'Other').label('cat_name'),
            func.coalesce(Category.color, '#6366f1').label('color'),
            func.sum(Transaction.amount).label('total_amount')
        ).outerjoin(Category, Transaction.category_id == Category.id).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.transaction_date >= first_of_month
        ).group_by(Category.name, Category.color).all()

        category_labels = [r.cat_name for r in cat_expenses] or ['No Expenses Yet']
        category_values = [float(r.total_amount) for r in cat_expenses] or [0]
        category_colors = [r.color for r in cat_expenses] or ['#94a3b8']

        # C. 6-Month Income vs Expense Trend
        month_labels = []
        monthly_income = []
        monthly_expense = []

        for i in range(5, -1, -1):
            m_date = today.replace(day=1) - timedelta(days=i * 28)
            m_start = date(m_date.year, m_date.month, 1)
            # Find last day of month
            if m_start.month == 12:
                m_end = date(m_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                m_end = date(m_start.year, m_start.month + 1, 1) - timedelta(days=1)

            month_labels.append(m_start.strftime('%b %Y'))

            inc = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
                Transaction.user_id == user_id,
                Transaction.type == 'income',
                Transaction.transaction_date >= m_start,
                Transaction.transaction_date <= m_end
            ).scalar()
            monthly_income.append(float(inc))

            exp = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
                Transaction.user_id == user_id,
                Transaction.type == 'expense',
                Transaction.transaction_date >= m_start,
                Transaction.transaction_date <= m_end
            ).scalar()
            monthly_expense.append(float(exp))

        return {
            'weekly_tasks': {
                'labels': week_labels,
                'completed': completed_counts,
                'created': created_counts
            },
            'expense_categories': {
                'labels': category_labels,
                'values': category_values,
                'colors': category_colors
            },
            'monthly_flow': {
                'labels': month_labels,
                'income': monthly_income,
                'expenses': monthly_expense
            }
        }
