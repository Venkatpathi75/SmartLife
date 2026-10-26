def test_create_and_get_task(auth_client):
    create_res = auth_client.post('/api/tasks', json={
        'title': 'Prepare Quarterly Financials',
        'description': 'Gather balance sheets and review expenses',
        'priority': 'high',
        'due_date': '2026-11-15T10:00:00',
        'checklists': ['Download bank statements', 'Reconcile invoices']
    })
    assert create_res.status_code == 201
    task = create_res.get_json()['data']
    assert task['title'] == 'Prepare Quarterly Financials'
    assert len(task['checklist_items']) == 2
    task_id = task['id']

    list_res = auth_client.get('/api/tasks')
    assert list_res.status_code == 200
    tasks = list_res.get_json()['data']
    assert len(tasks) == 1
    assert tasks[0]['id'] == task_id


def test_task_status_toggle(auth_client):
    create_res = auth_client.post('/api/tasks', json={'title': 'Review Contracts'})
    task_id = create_res.get_json()['data']['id']

    toggle_res = auth_client.patch(f'/api/tasks/{task_id}/status', json={'status': 'completed'})
    assert toggle_res.status_code == 200
    assert toggle_res.get_json()['data']['status'] == 'completed'
    assert toggle_res.get_json()['data']['completed_at'] is not None

    reopen_res = auth_client.patch(f'/api/tasks/{task_id}/status', json={'status': 'pending'})
    assert reopen_res.status_code == 200
    assert reopen_res.get_json()['data']['status'] == 'pending'
    assert reopen_res.get_json()['data']['completed_at'] is None


def test_task_data_isolation(client, user1, user2):
    """Verifies that User 2 cannot access, update, or delete User 1's task."""
    # 1. Login as User 1 (Alice) and create a private task
    login1 = client.post('/api/auth/login', json={'email': 'alice@example.com', 'password': 'Password123!'})
    assert login1.status_code == 200
    res1 = client.post('/api/tasks', json={'title': "Alice Confidential Task"})
    assert res1.status_code == 201
    task_id = res1.get_json()['data']['id']
    client.post('/api/auth/logout')

    # 2. Login as User 2 (Bob) and attempt unauthorized actions on Alice's task
    login2 = client.post('/api/auth/login', json={'email': 'bob@example.com', 'password': 'Password123!'})
    assert login2.status_code == 200

    # Bob tries to GET Alice's task -> 404 Not Found (Data Isolation)
    get_res = client.get(f'/api/tasks/{task_id}')
    assert get_res.status_code == 404

    # Bob tries to UPDATE Alice's task -> 404 Not Found
    update_res = client.put(f'/api/tasks/{task_id}', json={'title': 'Hijacked Task'})
    assert update_res.status_code == 404

    # Bob tries to DELETE Alice's task -> 404 Not Found
    del_res = client.delete(f'/api/tasks/{task_id}')
    assert del_res.status_code == 404
    client.post('/api/auth/logout')

    # 3. Anonymous attempt -> 401 Unauthorized
    anon_res = client.get(f'/api/tasks/{task_id}')
    assert anon_res.status_code == 401

    # 4. Login back as Alice and verify her task is intact
    client.post('/api/auth/login', json={'email': 'alice@example.com', 'password': 'Password123!'})
    confirm_res = client.get(f'/api/tasks/{task_id}')
    assert confirm_res.status_code == 200
    assert confirm_res.get_json()['data']['title'] == "Alice Confidential Task"
