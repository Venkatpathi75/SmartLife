const Budgets = {
    categories: [],

    init() {
        this.bindEvents();
    },

    bindEvents() {
        const form = document.getElementById('budget-form');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.saveBudget();
            });
        }
    },

    async ensureCategoriesLoaded() {
        if (!this.categories || this.categories.length === 0) {
            const catRes = await API.get('/api/transactions/categories?type=expense');
            if (catRes.ok && catRes.data) {
                this.categories = catRes.data;
            }
        }
    },

    async loadBudgets() {
        if (!Auth.currentUser) return;
        await this.ensureCategoriesLoaded();

        const res = await API.get('/api/budgets');
        const container = document.getElementById('budgets-container');
        const alertsContainer = document.getElementById('budget-alerts-container');
        if (!container) return;

        const sym = window.CURRENCY_SYMBOL || '₹';

        if (!res.ok || !res.data || res.data.length === 0) {
            container.innerHTML = `
                <div class="empty-state-box">
                    <i class="fa-solid fa-wallet empty-state-icon"></i>
                    <p style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">No Budget Plans Set</p>
                    <p style="color: var(--text-muted); margin-bottom: 1.25rem;">Create a budget to track spending ceilings and save systematically.</p>
                    <button class="btn btn-secondary" onclick="Budgets.openCreateModal()">
                        <i class="fa-solid fa-plus"></i> Create Budget Plan
                    </button>
                </div>`;
            if (alertsContainer) alertsContainer.innerHTML = '';
            return;
        }

        if (alertsContainer) {
            const exceededBudgets = res.data.filter(b => b.is_active && b.status === 'exceeded');
            const warningBudgets = res.data.filter(b => b.is_active && b.status === 'warning');

            let alertHtml = '';
            if (exceededBudgets.length > 0) {
                alertHtml += `
                    <div class="alert-banner danger">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                        <span><strong>Budget Alert:</strong> You have exceeded spending limits on "${exceededBudgets.map(b => b.name).join(', ')}".</span>
                    </div>`;
            } else if (warningBudgets.length > 0) {
                alertHtml += `
                    <div class="alert-banner warning">
                        <i class="fa-solid fa-circle-exclamation"></i>
                        <span><strong>Budget Warning:</strong> You have consumed over 75% of your planned allowance on "${warningBudgets.map(b => b.name).join(', ')}".</span>
                    </div>`;
            }
            alertsContainer.innerHTML = alertHtml;
        }

        container.innerHTML = res.data.map(b => this.renderBudgetCard(b, sym)).join('');
    },

    renderBudgetCard(b, sym) {
        let progressClass = 'progress-safe';
        let statusBadge = '<span class="badge" style="background-color: var(--success-light); color: var(--success);">On Track</span>';

        if (b.status === 'warning') {
            progressClass = 'progress-warning';
            statusBadge = '<span class="badge" style="background-color: var(--warning-light); color: var(--warning);">75%+ Used</span>';
        } else if (b.status === 'exceeded') {
            progressClass = 'progress-danger';
            statusBadge = '<span class="badge" style="background-color: var(--danger-light); color: var(--danger);">Exceeded</span>';
        }

        const barWidth = Math.min(b.percent_used, 100);

        let categoriesHtml = '';
        if (b.categories && b.categories.length > 0) {
            categoriesHtml = `
                <div class="budget-category-section">
                    <span style="font-size: 0.8rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">Category Allocations</span>
                    <div class="budget-category-grid">
                        ${b.categories.map(c => `
                            <div class="budget-category-chip">
                                <div class="chip-header">
                                    <span class="chip-name"><i class="fa-solid ${c.category_icon}" style="color: ${c.category_color};"></i> ${c.category_name}</span>
                                    <span style="font-weight: 600; color: ${c.is_exceeded ? 'var(--danger)' : 'var(--text-main)'};">
                                        ${sym} ${c.spent.toLocaleString()} / ${c.limit_amount.toLocaleString()}
                                    </span>
                                </div>
                                <div class="progress-container" style="height: 6px; margin: 0.35rem 0 0.1rem;">
                                    <div class="progress-fill ${c.is_exceeded ? 'progress-danger' : (c.percent_used >= 75 ? 'progress-warning' : 'progress-safe')}" style="width: ${Math.min(c.percent_used, 100)}%;"></div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>`;
        }

        return `
            <div class="budget-card status-${b.status}" id="budget-card-${b.id}">
                <div class="budget-header">
                    <div class="budget-title-wrap">
                        <h3 style="font-size: 1.15rem; font-weight: 700; color: var(--text-main);">${b.name}</h3>
                        <span class="budget-period-badge">${b.period.toUpperCase()}</span>
                        ${statusBadge}
                    </div>
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="btn-icon-subtle" title="Edit Budget" onclick="Budgets.openEditModal(${b.id})">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                        <button class="btn-icon-subtle delete" title="Delete Budget" onclick="Budgets.deleteBudget(${b.id})">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                </div>

                <div class="progress-container">
                    <div class="progress-fill ${progressClass}" style="width: ${barWidth}%;"></div>
                </div>

                <div class="budget-metrics-row">
                    <div>
                        Spent: <strong>${sym} ${b.spent.toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong> of ${sym} ${b.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                    <div>
                        ${b.remaining >= 0 ? 'Remaining: ' : 'Over budget: '}
                        <strong style="color: ${b.remaining < 0 ? 'var(--danger)' : 'inherit'};">
                            ${sym} ${Math.abs(b.remaining).toLocaleString(undefined, { minimumFractionDigits: 2 })} (${b.percent_used}%)
                        </strong>
                    </div>
                    <div style="font-size: 0.8rem; color: var(--text-subtle);">
                        Period: ${b.start_date} to ${b.end_date}
                    </div>
                </div>

                ${categoriesHtml}
            </div>`;
    },

    async openCreateModal() {
        if (!Auth.currentUser) {
            Auth.showModal('login');
            return;
        }

        await this.ensureCategoriesLoaded();

        document.getElementById('budget-modal-title').textContent = 'Create Budget Plan';
        document.getElementById('budget-id-field').value = '';
        document.getElementById('budget-form').reset();
        document.getElementById('budget-category-inputs').innerHTML = '';

        const now = new Date();
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);

        const toLocalISO = (d) => {
            const yr = d.getFullYear();
            const mo = String(d.getMonth() + 1).padStart(2, '0');
            const da = String(d.getDate()).padStart(2, '0');
            return `${yr}-${mo}-${da}`;
        };

        document.getElementById('budget-start-input').value = toLocalISO(firstDay);
        document.getElementById('budget-end-input').value = toLocalISO(lastDay);
        document.getElementById('budget-currency-label').textContent = window.CURRENCY_SYMBOL || '₹';

        document.getElementById('budget-modal').classList.add('active');
    },

    async openEditModal(budgetId) {
        await this.ensureCategoriesLoaded();

        const res = await API.get(`/api/budgets/${budgetId}`);
        if (!res.ok) return;

        const b = res.data;
        document.getElementById('budget-modal-title').textContent = 'Edit Budget Plan';
        document.getElementById('budget-id-field').value = b.id;
        document.getElementById('budget-name-input').value = b.name;
        document.getElementById('budget-amount-input').value = b.amount;
        document.getElementById('budget-period-input').value = b.period;
        document.getElementById('budget-start-input').value = b.start_date;
        document.getElementById('budget-end-input').value = b.end_date;

        const container = document.getElementById('budget-category-inputs');
        container.innerHTML = '';
        if (b.category_limits) {
            b.category_limits.forEach(cl => {
                this.addCategoryAllocationRow(cl.category_id, cl.limit_amount);
            });
        }

        document.getElementById('budget-modal').classList.add('active');
    },

    closeModal() {
        document.getElementById('budget-modal').classList.remove('active');
    },

    addCategoryAllocationRow(selectedCatId = '', amountVal = '') {
        const container = document.getElementById('budget-category-inputs');
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.gap = '0.5rem';
        row.style.alignItems = 'center';

        const catOptions = this.categories.map(c => 
            `<option value="${c.id}" ${c.id == selectedCatId ? 'selected' : ''}>${c.name}</option>`
        ).join('');

        row.innerHTML = `
            <select class="form-input budget-cat-select" style="flex: 2;">
                <option value="">Select Category...</option>
                ${catOptions}
            </select>
            <input type="number" step="0.01" min="0.01" class="form-input budget-cat-amount" placeholder="Limit (${window.CURRENCY_SYMBOL || '₹'})" value="${amountVal}" style="flex: 1.5;">
            <button type="button" class="btn btn-outline" style="padding: 0.45rem 0.65rem;" onclick="this.parentElement.remove()">
                <i class="fa-solid fa-xmark"></i>
            </button>`;
        container.appendChild(row);
    },

    async saveBudget() {
        const budgetId = document.getElementById('budget-id-field').value;
        const name = document.getElementById('budget-name-input').value.trim();
        const amount = document.getElementById('budget-amount-input').value;
        const period = document.getElementById('budget-period-input').value;
        const start_date = document.getElementById('budget-start-input').value;
        const end_date = document.getElementById('budget-end-input').value;

        const catSelects = document.querySelectorAll('.budget-cat-select');
        const catAmounts = document.querySelectorAll('.budget-cat-amount');
        const category_limits = [];

        for (let i = 0; i < catSelects.length; i++) {
            const catId = catSelects[i].value;
            const limitAmt = catAmounts[i].value;
            if (catId && limitAmt) {
                category_limits.push({ category_id: parseInt(catId), limit_amount: limitAmt });
            }
        }

        const payload = {
            name,
            amount,
            period,
            start_date,
            end_date,
            category_limits
        };

        let res;
        if (budgetId) {
            res = await API.put(`/api/budgets/${budgetId}`, payload);
        } else {
            res = await API.post('/api/budgets', payload);
        }

        if (res.ok) {
            API.showToast(res.message, 'success');
            this.closeModal();
            await this.loadBudgets();
            if (window.Dashboard) Dashboard.loadDashboard();
        }
    },

    async deleteBudget(budgetId) {
        if (!confirm('Are you sure you want to delete this budget plan?')) return;

        const res = await API.delete(`/api/budgets/${budgetId}`);
        if (res.ok) {
            API.showToast('Budget deleted.', 'info');
            await this.loadBudgets();
            if (window.Dashboard) Dashboard.loadDashboard();
        }
    }
};

window.Budgets = Budgets;
document.addEventListener('DOMContentLoaded', () => Budgets.init());
