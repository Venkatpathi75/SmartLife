import os
import click
from app import create_app, db
from app.models.user import User

config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)


@app.cli.command("init-db")
def init_db():
    """Create all database tables."""
    with app.app_context():
        db.create_all()
        click.echo("✓ Database tables initialized successfully.")


@app.cli.command("create-admin")
@click.option('--name', prompt='Admin name', help='Administrator full name.')
@click.option('--email', prompt='Admin email', help='Administrator email address.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password.')
def create_admin(name, email, password):
    """Securely creates a designated system administrator account."""
    with app.app_context():
        email_clean = email.strip().lower()
        existing = User.query.filter_by(email=email_clean).first()
        if existing:
            click.echo(f"Error: A user with email {email_clean} already exists.")
            return

        admin = User(
            name=name.strip(),
            email=email_clean,
            role='admin',
            currency='INR'
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"✓ Administrator account '{email_clean}' created successfully.")


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
