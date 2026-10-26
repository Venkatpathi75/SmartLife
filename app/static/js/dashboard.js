const Dashboard = {
    weeklyChart: null,
    categoryChart: null,

    async loadDashboard() {
        if (!Auth.currentUser) return;
        
        await Promise.all([
            this.fetchSummary(),
            this.fetchCharts(),
            this.fetchRecentActivity()
        ]);
    },

    async fetchSummary() {
        const res = await API.get('/api/dashboard/summary');
        if (!res.ok) return;

        const data = res.data;
        const sym = window.CURRENCY_SYMBOL || '₹';

        // Update Task Stat Cards
        document.getElementById('stat-total-tasks').textContent = data.tasks.total;
        document.getElementById('stat-completed-tasks').textContent = data.tasks.completed;
        document.getElementById('stat-pending-tasks').textContent = data.tasks.pending;
        document.getElementById('stat-overdue-tasks').textContent = data.tasks.overdue;

        // Update Finance Stat Cards
        document.getElementById('stat-total-income').textContent = `${sym} ${data.finances.income.toLocaleString()}`;
        document.getElementById('stat-total-expenses').textContent = `${sym} ${data.finances.expenses.toLocaleString()}`;
        document.getElementById('stat-net-savings').textContent = `${sym} ${data.finances.savings.toLocaleString()}`;
        document.getElementById('stat-remaining-budget').textContent = data.finances.has_active_budget 
            ? `${sym} ${data.finances.remaining_budget.toLocaleString()}`
            : 'No Active Budget';
    },

    async fetchCharts() {
        const res = await API.get('/api/dashboard/charts');
        if (!res.ok) return;

        const data = res.data;
        this.renderWeeklyChart(data.weekly_tasks);
        this.renderCategoryChart(data.expense_categories);
    },

    renderWeeklyChart(taskData) {
        const ctx = document.getElementById('chart-weekly-tasks');
        if (!ctx) return;

        if (this.weeklyChart) this.weeklyChart.destroy();

        this.weeklyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: taskData.labels,
                datasets: [
                    {
                        label: 'Tasks Completed',
                        data: taskData.completed,
                        backgroundColor: '#4f46e5',
                        borderRadius: 6
                    },
                    {
                        label: 'Tasks Created',
                        data: taskData.created,
                        backgroundColor: '#cbd5e1',
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top' }
                },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } }
                }
            }
        });
    },

    renderCategoryChart(catData) {
        const ctx = document.getElementById('chart-expense-categories');
        if (!ctx) return;

        if (this.categoryChart) this.categoryChart.destroy();

        this.categoryChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: catData.labels,
                datasets: [{
                    data: catData.values,
                    backgroundColor: catData.colors,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    },

    async fetchRecentActivity() {
        const res = await API.get('/api/dashboard/recent-activity');
        if (!res.ok) return;

        const tasksContainer = document.getElementById('recent-tasks-list');
        const txContainer = document.getElementById('recent-tx-list');

        if (tasksContainer) {
            if (res.data.tasks.length === 0) {
                tasksContainer.innerHTML = '<p class="empty-state">No tasks created yet. Click "Add Task" to get started!</p>';
            } else {
                tasksContainer.innerHTML = res.data.tasks.map(t => `
                    <div class="activity-row">
                        <span class="badge badge-${t.priority}">${t.priority}</span>
                        <span class="activity-title">${t.title}</span>
                        <span class="activity-status">${t.status}</span>
                    </div>
                `).join('');
            }
        }

        if (txContainer) {
            const sym = window.CURRENCY_SYMBOL || '₹';
            if (res.data.transactions.length === 0) {
                txContainer.innerHTML = '<p class="empty-state">No transactions recorded this month.</p>';
            } else {
                txContainer.innerHTML = res.data.transactions.map(tx => `
                    <div class="activity-row">
                        <i class="fa-solid ${tx.category_icon}"></i>
                        <span class="activity-title">${tx.title}</span>
                        <span class="activity-amount ${tx.type === 'income' ? 'text-success' : 'text-danger'}">
                            ${tx.type === 'income' ? '+' : '-'}${sym} ${tx.amount.toLocaleString()}
                        </span>
                    </div>
                `).join('');
            }
        }
    }
};

window.Dashboard = Dashboard;
