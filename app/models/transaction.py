from datetime import datetime, timezone, date
from decimal import Decimal
from app import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)  # Null = system default
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'expense', 'income', or 'both'
    icon = db.Column(db.String(50), nullable=False, default='fa-tag')
    color = db.Column(db.String(20), nullable=False, default='#4f46e5')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tasks = db.relationship('Task', backref='category', lazy=True)
    transactions = db.relationship('Transaction', backref='category', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'type': self.type,
            'icon': self.icon,
            'color': self.color
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)  # Exact decimal for monetary calculations
    type = db.Column(db.String(20), nullable=False)        # 'income' or 'expense'
    transaction_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    payment_method = db.Column(db.String(50), nullable=False, default='UPI / Cash')
    merchant = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else 'General',
            'category_icon': self.category.icon if self.category else 'fa-receipt',
            'category_color': self.category.color if self.category else '#64748b',
            'title': self.title,
            'amount': float(self.amount) if self.amount is not None else 0.0,
            'type': self.type,
            'transaction_date': self.transaction_date.isoformat(),
            'payment_method': self.payment_method,
            'merchant': self.merchant,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
