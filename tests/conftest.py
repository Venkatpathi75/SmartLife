import pytest
from app import create_app, db
from app.models.user import User
from app.models.transaction import Category


@pytest.fixture
def app():
    app = create_app('testing')

    with app.app_context():
        db.create_all()
        db.session.add(Category(user_id=None, name='Groceries', type='expense', icon='fa-utensils', color='#ef4444'))
        db.session.add(Category(user_id=None, name='Salary', type='income', icon='fa-money-bill-wave', color='#10b981'))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """An unauthenticated test client."""
    return app.test_client()


@pytest.fixture
def user1(app):
    with app.app_context():
        user = User(name='Alice Tester', email='alice@example.com', role='user', currency='INR')
        user.set_password('Password123!')
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def user2(app):
    with app.app_context():
        user = User(name='Bob Isolation', email='bob@example.com', role='user', currency='USD')
        user.set_password('Password123!')
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def admin_user(app):
    with app.app_context():
        admin = User(name='Admin Supervisor', email='admin@example.com', role='admin', currency='INR')
        admin.set_password('AdminSecret123!')
        db.session.add(admin)
        db.session.commit()
        return admin.id


@pytest.fixture
def auth_client(app, user1):
    """Independent test client logged in as User 1 (Alice)."""
    c = app.test_client()
    res = c.post('/api/auth/login', json={'email': 'alice@example.com', 'password': 'Password123!'})
    assert res.status_code == 200
    return c


@pytest.fixture
def user2_client(app, user2):
    """Independent test client logged in as User 2 (Bob)."""
    c = app.test_client()
    res = c.post('/api/auth/login', json={'email': 'bob@example.com', 'password': 'Password123!'})
    assert res.status_code == 200
    return c


@pytest.fixture
def admin_client(app, admin_user):
    """Independent test client logged in as Administrator."""
    c = app.test_client()
    res = c.post('/api/auth/login', json={'email': 'admin@example.com', 'password': 'AdminSecret123!'})
    assert res.status_code == 200
    return c
