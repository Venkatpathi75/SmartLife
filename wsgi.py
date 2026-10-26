import os
from app import create_app, db
from app.models.user import User
from app.routes.transactions import ensure_default_categories

config_name = os.environ.get('FLASK_ENV', 'production')
app = create_app(config_name)

# Automatically create PostgreSQL tables and seed data on startup
with app.app_context():
    try:
        db.create_all()
        ensure_default_categories()

        # Optional: Auto-provision admin if configured in environment
        admin_email = os.environ.get('ADMIN_EMAIL')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        admin_name = os.environ.get('ADMIN_NAME', 'System Administrator')

        if admin_email and admin_password:
            clean_email = admin_email.strip().lower()
            existing_admin = User.query.filter_by(email=clean_email).first()
            if not existing_admin:
                admin = User(
                    name=admin_name,
                    email=clean_email,
                    role='admin',
                    currency='INR'
                )
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()
                print(f"✓ Auto-provisioned admin account: {clean_email}")
    except Exception as e:
        print(f"Database initialization note: {e}")
