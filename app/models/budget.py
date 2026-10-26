from datetime import datetime, timezone, date
from decimal import Decimal
from app import db


class Budget(db.Model):
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    period = db.Column(db.String(20), nullable=False, default='monthly')
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    categories = db.relationship('BudgetCategory', backref='budget', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'amount': float(self.amount),
            'period': self.period,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'category_limits': [item.to_dict() for item in self.categories]
        }


class BudgetCategory(db.Model):
    __tablename__ = 'budget_categories'

    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('budgets.id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    limit_amount = db.Column(db.Numeric(12, 2), nullable=False)

    category = db.relationship('Category', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'budget_id': self.budget_id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'limit_amount': float(self.limit_amount)
        }
