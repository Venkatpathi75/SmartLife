def test_register_success(client):
    res = client.post('/api/auth/register', json={
        'name': 'New User',
        'email': 'newuser@example.com',
        'password': 'StrongPassword123!',
        'currency': 'INR'
    })
    assert res.status_code == 201
    json_data = res.get_json()
    assert json_data['success'] is True
    assert json_data['data']['user']['email'] == 'newuser@example.com'
    assert json_data['data']['user']['role'] == 'user'  # Security: cannot self-elevate


def test_register_duplicate_email(client, user1):
    res = client.post('/api/auth/register', json={
        'name': 'Alice Imposter',
        'email': 'alice@example.com',
        'password': 'AnotherPassword123!'
    })
    assert res.status_code == 409
    assert res.get_json()['error']['code'] == 'EMAIL_EXISTS'


def test_register_invalid_inputs(client):
    # Short password
    res = client.post('/api/auth/register', json={
        'name': 'Test',
        'email': 'valid@example.com',
        'password': '123'
    })
    assert res.status_code == 400
    assert res.get_json()['error']['code'] == 'INVALID_PASSWORD'

    # Malformed email
    res = client.post('/api/auth/register', json={
        'name': 'Test',
        'email': 'not-an-email',
        'password': 'StrongPassword123!'
    })
    assert res.status_code == 400
    assert res.get_json()['error']['code'] == 'INVALID_EMAIL'


def test_login_success_and_logout(client, user1):
    login_res = client.post('/api/auth/login', json={
        'email': 'alice@example.com',
        'password': 'Password123!'
    })
    assert login_res.status_code == 200
    assert login_res.get_json()['success'] is True

    # Check authenticated session
    me_res = client.get('/api/auth/me')
    assert me_res.status_code == 200
    assert me_res.get_json()['data']['authenticated'] is True
    assert me_res.get_json()['data']['user']['email'] == 'alice@example.com'

    # Logout
    logout_res = client.post('/api/auth/logout')
    assert logout_res.status_code == 200

    # Verify session is terminated
    me_after = client.get('/api/auth/me')
    assert me_after.get_json()['data']['authenticated'] is False


def test_login_invalid_credentials(client, user1):
    res = client.post('/api/auth/login', json={
        'email': 'alice@example.com',
        'password': 'WrongPassword!'
    })
    assert res.status_code == 401
    assert res.get_json()['error']['code'] == 'INVALID_CREDENTIALS'


def test_update_profile(auth_client):
    res = auth_client.put('/api/auth/profile', json={
        'name': 'Alice Updated',
        'currency': 'USD',
        'theme': 'dark'
    })
    assert res.status_code == 200
    user_data = res.get_json()['data']['user']
    assert user_data['name'] == 'Alice Updated'
    assert user_data['currency'] == 'USD'
    assert user_data['theme'] == 'dark'
