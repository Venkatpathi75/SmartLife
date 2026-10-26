const Reports = {
    init() {
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);

        const startInput = document.getElementById('report-start-date');
        const endInput = document.getElementById('report-end-date');

        if (startInput) startInput.value = firstDay.toISOString().split('T')[0];
        if (endInput) endInput.value = today.toISOString().split('T')[0];
    },

    async loadReports() {
        if (!Auth.currentUser) return;

        const startDate = document.getElementById('report-start-date')?.value || '';
        const endDate = document.getElementById('report-end-date')?.value || '';

        const url = `/api/reports/analytics?start_date=${startDate}&end_date=${endDate}`;
        const res = await API.get(url);
        if (!res.ok) return;

        const data = res.data;
        const sym = window.CURRENCY_SYMBOL || '₹';

        // Render Task Velocity
        document.getElementById('report-total-tasks').textContent = data.tasks.total;
        document.getElementById('report-completed-tasks').textContent = data.tasks.completed;
        document.getElementById('report-completion-rate').textContent = `${data.tasks.completion_rate}%`;
        document.getElementById('report-overdue-tasks').textContent = data.tasks.overdue;

        // Render Cash Flow
        document.getElementById('report-income-total').textContent = `${sym} ${data.finances.total_income.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
        document.getElementById('report-expense-total').textContent = `${sym} ${data.finances.total_expense.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
        
        const netFlowEl = document.getElementById('report-net-flow');
        const isSurplus = data.finances.net_cash_flow >= 0;
        netFlowEl.textContent = `${isSurplus ? '+' : '-'}${sym} ${Math.abs(data.finances.net_cash_flow).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
        netFlowEl.className = `stat-value ${isSurplus ? 'text-success' : 'text-danger'}`;

        document.getElementById('report-savings-rate').textContent = `${data.finances.savings_rate}%`;

        // Render Category Allocations Table
        const catTbody = document.getElementById('report-categories-body');
        if (catTbody) {
            if (data.categories.length === 0) {
                catTbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 2rem; color: var(--text-muted);">No expenses recorded for this timeframe.</td></tr>';
            } else {
                catTbody.innerHTML = data.categories.map(c => `
                    <tr>
                        <td>
                            <span class="category-pill" style="background-color: ${c.color}18; color: ${c.color};">
                                <i class="fa-solid ${c.icon}"></i> ${c.name}
                            </span>
                        </td>
                        <td>${c.count} transactions</td>
                        <td><strong>${sym} ${c.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong></td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <div class="progress-container" style="flex: 1; height: 6px; margin: 0;">
                                    <div class="progress-fill" style="width: ${c.percentage}%; background-color: ${c.color};"></div>
                                </div>
                                <span style="font-size: 0.8rem; font-weight: 600; width: 45px;">${c.percentage}%</span>
                            </div>
                        </td>
                    </tr>
                `).join('');
            }
        }
    }
};

window.Reports = Reports;
document.addEventListener('DOMContentLoaded', () => Reports.init());
