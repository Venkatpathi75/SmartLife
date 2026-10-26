def test_monetary_exact_precision(auth_client):
    """Validates that floating-point rounding issues do not occur."""
    # Record income: 1000.10
    auth_client.post('/api/transactions', json={
        'title': 'Stipend',
        'type': 'income',
        'amount': '1000.10',
        'transaction_date': '2026-11-01'
    })

    # Record expense 1: 300.20
    auth_client.post('/api/transactions', json={
        'title': 'Office supplies',
        'type': 'expense',
        'amount': '300.20',
        'transaction_date': '2026-11-02'
    })

    # Record expense 2: 200.70
    auth_client.post('/api/transactions', json={
        'title': 'Team lunch',
        'type': 'expense',
        'amount': '200.70',
        'transaction_date': '2026-11-03'
    })

    # Total Expenses should be exactly 500.90, Net flow should be exactly 499.20
    res = auth_client.get('/api/transactions')
    assert res.status_code == 200
    summary = res.get_json()['summary']

    assert summary['total_income'] == 1000.10
    assert summary['total_expense'] == 500.90
    assert summary['net_cash_flow'] == 499.20


def test_budget_threshold_states(auth_client):
    """Tests budget utilization percentage and threshold status (safe -> warning -> exceeded)."""
    # 1. Create a 1000.00 budget
    b_res = auth_client.post('/api/budgets', json={
        'name': 'November Household Budget',
        'amount': '1000.00',
        'start_date': '2026-11-01',
        'end_date': '2026-11-30'
    })
    assert b_res.status_code == 201

    # Check initially safe
    budgets_res = auth_client.get('/api/budgets')
    b_data = budgets_res.get_json()['data'][0]
    assert b_data['status'] == 'safe'
    assert b_data['spent'] == 0.0

    # Add expense reaching 800.00 (80% -> warning status)
    auth_client.post('/api/transactions', json={
        'title': 'Maintenance bill',
        'type': 'expense',
        'amount': '800.00',
        'transaction_date': '2026-11-10'
    })

    budgets_res2 = auth_client.get('/api/budgets')
    b_data2 = budgets_res2.get_json()['data'][0]
    assert b_data2['status'] == 'warning'
    assert b_data2['percent_used'] == 80.0
    assert b_data2['remaining'] == 200.0

    # Add expense exceeding limit (800 + 250 = 1050.00 -> exceeded status)
    auth_client.post('/api/transactions', json={
        'title': 'Extra expense',
        'type': 'expense',
        'amount': '250.00',
        'transaction_date': '2026-11-12'
    })

    budgets_res3 = auth_client.get('/api/budgets')
    b_data3 = budgets_res3.get_json()['data'][0]
    assert b_data3['status'] == 'exceeded'
    assert b_data3['percent_used'] == 105.0
    assert b_data3['remaining'] == -50.0


def test_transactions_csv_export(auth_client):
    auth_client.post('/api/transactions', json={
        'title': 'Consulting Fee',
        'type': 'income',
        'amount': '5000.00',
        'transaction_date': '2026-11-01'
    })

    res = auth_client.get('/api/transactions/export/csv')
    assert res.status_code == 200
    assert res.headers['Content-Type'].startswith('text/csv')
    csv_text = res.get_data(as_text=True)
    assert 'Consulting Fee' in csv_text
    assert '5000.00' in csv_text
