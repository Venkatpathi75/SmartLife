from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    is_active_account = db.Column(db.Boolean, nullable=False, default=True)
    currency = db.Column(db.String(10), nullable=False, default='INR')
    timezone = db.Column(db.String(50), nullable=False, default='Asia/Kolkata')
    theme = db.Column(db.String(10), nullable=False, default='light')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    @property
    def is_active(self):
        """Overrides Flask-Login property to check account status."""
        return self.is_active_account

    def set_password(self, password):
        """Hashes and sets the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifies candidate password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Serializes user info safely, excluding sensitive credentials."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active_account,
            'currency': self.currency,
            'timezone': self.timezone,
            'theme': self.theme,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
