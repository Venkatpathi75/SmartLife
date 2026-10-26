def test_calendar_events_and_reschedule(auth_client):
    t_res = auth_client.post('/api/tasks', json={
        'title': 'Team Sprint Planning',
        'due_date': '2026-11-10T10:00:00'
    })
    task_id = t_res.get_json()['data']['id']

    events_res = auth_client.get('/api/calendar/events?start=2026-11-01T00:00:00Z&end=2026-11-30T23:59:59Z')
    assert events_res.status_code == 200
    events = events_res.get_json()['data']
    assert any(e['taskId'] == task_id for e in events)

    reschedule_res = auth_client.patch(f'/api/calendar/events/{task_id}/reschedule', json={
        'new_date': '2026-11-18T14:30:00Z'
    })
    assert reschedule_res.status_code == 200
    assert '2026-11-18' in reschedule_res.get_json()['data']['due_date']


def test_admin_rbac_protection(app, user1, admin_user):
    """Ensures anonymous and regular users are strictly blocked from admin endpoints."""
    # 1. Anonymous request -> 401
    anon_client = app.test_client()
    anon_res = anon_client.get('/api/admin/stats')
    assert anon_res.status_code == 401

    # 2. Regular user request -> 403 Forbidden
    reg_client = app.test_client()
    reg_client.post('/api/auth/login', json={'email': 'alice@example.com', 'password': 'Password123!'})
    user_res = reg_client.get('/api/admin/stats')
    assert user_res.status_code == 403
    assert user_res.get_json()['error']['code'] == 'FORBIDDEN'

    # 3. Admin request -> 200 OK
    adm_client = app.test_client()
    adm_client.post('/api/auth/login', json={'email': 'admin@example.com', 'password': 'AdminSecret123!'})
    admin_res = adm_client.get('/api/admin/stats')
    assert admin_res.status_code == 200
    data = admin_res.get_json()['data']
    assert 'users' in data
    assert 'finances' in data


def test_admin_toggle_user_status_and_audit_log(admin_client, user1, admin_user):
    suspend_res = admin_client.patch(f'/api/admin/users/{user1}/status')
    assert suspend_res.status_code == 200
    assert suspend_res.get_json()['data']['is_active'] is False

    audit_res = admin_client.get('/api/admin/audit-logs')
    assert audit_res.status_code == 200
    logs = audit_res.get_json()['data']
    assert len(logs) > 0
    assert logs[0]['action'] == 'USER_STATUS_DEACTIVATED'
    assert logs[0]['target_id'] == user1

    self_res = admin_client.patch(f'/api/admin/users/{admin_user}/status')
    assert self_res.status_code == 400
    assert self_res.get_json()['error']['code'] == 'SELF_LOCKOUT_FORBIDDEN'
