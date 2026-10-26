const Finances = {
    categories: [],
    searchDebounce: null,

    init() {
        this.bindEvents();
    },

    bindEvents() {
        // Search & Filters for Expenses
        const expSearch = document.getElementById('expense-search-input');
        if (expSearch) {
            expSearch.addEventListener('input', () => {
                clearTimeout(this.searchDebounce);
                this.searchDebounce = setTimeout(() => this.loadTransactions('expense'), 300);
            });
        }
        document.getElementById('expense-category-filter')?.addEventListener('change', () => this.loadTransactions('expense'));
        document.getElementById('expense-start-date')?.addEventListener('change', () => this.loadTransactions('expense'));
        document.getElementById('expense-end-date')?.addEventListener('change', () => this.loadTransactions('expense'));

        // Search & Filters for Income
        const incSearch = document.getElementById('income-search-input');
        if (incSearch) {
            incSearch.addEventListener('input', () => {
                clearTimeout(this.searchDebounce);
                this.searchDebounce = setTimeout(() => this.loadTransactions('income'), 300);
            });
        }
        document.getElementById('income-category-filter')?.addEventListener('change', () => this.loadTransactions('income'));
        document.getElementById('income-start-date')?.addEventListener('change', () => this.loadTransactions('income'));
        document.getElementById('income-end-date')?.addEventListener('change', () => this.loadTransactions('income'));

        // Transaction Modal Form Submission
        const txForm = document.getElementById('tx-form');
        if (txForm) {
            txForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.saveTransaction();
            });
        }
    },

    async loadCategories(type = null) {
        let url = '/api/transactions/categories';
        if (type) url += `?type=${type}`;
        const res = await API.get(url);
        if (res.ok) {
            this.categories = res.data;
            this.populateCategorySelects();
        }
    },

    populateCategorySelects() {
        const expFilter = document.getElementById('expense-category-filter');
        const incFilter = document.getElementById('income-category-filter');
        const modalSelect = document.getElementById('tx-category-input');

        const activeType = document.querySelector('input[name="type"]:checked')?.value || 'expense';

        if (expFilter) {
            const expCats = this.categories.filter(c => c.type === 'expense' || c.type === 'both');
            expFilter.innerHTML = '<option value="">All Categories</option>' + 
                expCats.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        }

        if (incFilter) {
            const incCats = this.categories.filter(c => c.type === 'income' || c.type === 'both');
            incFilter.innerHTML = '<option value="">All Categories</option>' + 
                incCats.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        }

        if (modalSelect) {
            const filtered = this.categories.filter(c => c.type === activeType || c.type === 'both');
            modalSelect.innerHTML = '<option value="">Select Category...</option>' + 
                filtered.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        }
    },

    onTypeChange(type) {
        this.populateCategorySelects();
    },

    async loadTransactions(type) {
        if (!Auth.currentUser) return;
        await this.loadCategories();

        const search = document.getElementById(`${type}-search-input`)?.value || '';
        const catId = document.getElementById(`${type}-category-filter`)?.value || '';
        const startDate = document.getElementById(`${type}-start-date`)?.value || '';
        const endDate = document.getElementById(`${type}-end-date`)?.value || '';

        let url = `/api/transactions?type=${type}&search=${encodeURIComponent(search)}`;
        if (catId) url += `&category_id=${catId}`;
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;

        const res = await API.get(url);
        const tbody = document.getElementById(`${type}-table-body`);
        const totalEl = document.getElementById(`${type}-period-total`);
        const countEl = document.getElementById(`${type}-period-count`);

        if (!tbody) return;

        const sym = window.CURRENCY_SYMBOL || '₹';

        if (!res.ok || res.data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">No ${type} transactions recorded for this period.</td></tr>`;
            if (totalEl) totalEl.textContent = `${sym} 0.00`;
            if (countEl) countEl.textContent = '0 recorded items';
            return;
        }

        const totalAmount = type === 'expense' ? res.summary.total_expense : res.summary.total_income;
        if (totalEl) totalEl.textContent = `${sym} ${totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
        if (countEl) countEl.textContent = `${res.summary.count} recorded transactions`;

        tbody.innerHTML = res.data.map(tx => {
            const isInc = tx.type === 'income';
            return `
                <tr>
                    <td><strong>${tx.transaction_date}</strong></td>
                    <td>
                        <div style="font-weight: 600;">${tx.title}</div>
                        ${tx.merchant ? `<div style="font-size: 0.775rem; color: var(--text-muted);"><i class="fa-solid fa-shop"></i> ${tx.merchant}</div>` : ''}
                    </td>
                    <td>
                        <span class="category-pill" style="background-color: ${tx.category_color}18; color: ${tx.category_color};">
                            <i class="fa-solid ${tx.category_icon}"></i> ${tx.category_name}
                        </span>
                    </td>
                    <td><span style="font-size: 0.8rem; color: var(--text-subtle);">${tx.payment_method}</span></td>
                    <td class="${isInc ? 'amount-income' : 'amount-expense'}">
                        ${isInc ? '+' : '-'}${sym} ${tx.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td style="text-align: right;">
                        <button class="btn-icon-subtle" title="Edit" onclick="Finances.openEditModal(${tx.id})">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                        <button class="btn-icon-subtle delete" title="Delete" onclick="Finances.deleteTransaction(${tx.id})">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </td>
                </tr>`;
        }).join('');
    },

    openModal(defaultType = 'expense') {
        if (!Auth.currentUser) {
            Auth.showModal('login');
            return;
        }

        document.getElementById('tx-modal-title').textContent = defaultType === 'income' ? 'Record Income' : 'Record Expense';
        document.getElementById('tx-id-field').value = '';
        document.getElementById('tx-form').reset();
        
        if (defaultType === 'income') {
            document.getElementById('tx-type-income').checked = true;
        } else {
            document.getElementById('tx-type-expense').checked = true;
        }

        document.getElementById('tx-date-input').value = new Date().toISOString().split('T')[0];
        document.getElementById('tx-currency-label').textContent = window.CURRENCY_SYMBOL || '₹';
        
        this.populateCategorySelects();
        document.getElementById('tx-modal').classList.add('active');
    },

    async openEditModal(txId) {
        const res = await API.get(`/api/transactions/${txId}`);
        if (!res.ok) return;

        const tx = res.data;
        document.getElementById('tx-modal-title').textContent = 'Edit Transaction';
        document.getElementById('tx-id-field').value = tx.id;
        document.getElementById('tx-title-input').value = tx.title;
        document.getElementById('tx-amount-input').value = tx.amount;
        document.getElementById('tx-date-input').value = tx.transaction_date;
        document.getElementById('tx-method-input').value = tx.payment_method || 'UPI / Cash';
        document.getElementById('tx-merchant-input').value = tx.merchant || '';
        document.getElementById('tx-notes-input').value = tx.notes || '';

        if (tx.type === 'income') {
            document.getElementById('tx-type-income').checked = true;
        } else {
            document.getElementById('tx-type-expense').checked = true;
        }

        this.populateCategorySelects();
        document.getElementById('tx-category-input').value = tx.category_id || '';
        document.getElementById('tx-modal').classList.add('active');
    },

    closeModal() {
        document.getElementById('tx-modal').classList.remove('active');
    },

    async saveTransaction() {
        const txId = document.getElementById('tx-id-field').value;
        const type = document.querySelector('input[name="type"]:checked').value;
        const title = document.getElementById('tx-title-input').value.trim();
        const amount = document.getElementById('tx-amount-input').value;
        const transaction_date = document.getElementById('tx-date-input').value;
        const category_id = document.getElementById('tx-category-input').value;
        const payment_method = document.getElementById('tx-method-input').value;
        const merchant = document.getElementById('tx-merchant-input').value.trim();
        const notes = document.getElementById('tx-notes-input').value.trim();

        const payload = {
            type,
            title,
            amount,
            transaction_date,
            category_id: category_id || null,
            payment_method,
            merchant,
            notes
        };

        let res;
        if (txId) {
            res = await API.put(`/api/transactions/${txId}`, payload);
        } else {
            res = await API.post('/api/transactions', payload);
        }

        if (res.ok) {
            API.showToast(res.message, 'success');
            this.closeModal();
            this.loadTransactions(type);
            if (window.Dashboard) Dashboard.loadDashboard();
            if (window.CalendarApp) CalendarApp.refresh();
        }
    },

    async deleteTransaction(txId) {
        if (!confirm('Are you sure you want to delete this transaction record?')) return;

        const res = await API.delete(`/api/transactions/${txId}`);
        if (res.ok) {
            API.showToast('Transaction deleted.', 'info');
            this.loadTransactions('expense');
            this.loadTransactions('income');
            if (window.Dashboard) Dashboard.loadDashboard();
            if (window.CalendarApp) CalendarApp.refresh();
        }
    },

    exportCSV(type) {
        if (!Auth.currentUser) return;
        const startDate = document.getElementById(`${type}-start-date`)?.value || '';
        const endDate = document.getElementById(`${type}-end-date`)?.value || '';
        const catId = document.getElementById(`${type}-category-filter`)?.value || '';

        let url = `/api/transactions/export/csv?type=${type}`;
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;
        if (catId) url += `&category_id=${catId}`;

        window.location.href = url;
    }
};

window.Finances = Finances;
document.addEventListener('DOMContentLoaded', () => Finances.init());
