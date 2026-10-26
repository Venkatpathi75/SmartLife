const Finances = {
    categories: [],
    searchDebounce: null,

    CATEGORY_KEYWORDS: {
        'Food & Dining': ['food', 'dining', 'lunch', 'dinner', 'breakfast', 'meal', 'pizza', 'burger', 'restaurant', 'cafe', 'coffee', 'grocery', 'groceries', 'supermarket', 'snack', 'snacks', 'tea', 'swiggy', 'zomato', 'eat', 'bakery', 'milk', 'vegetables', 'fruit'],
        'Transportation': ['transport', 'travel', 'cab', 'taxi', 'uber', 'ola', 'auto', 'bus', 'metro', 'train', 'flight', 'petrol', 'fuel', 'gas', 'diesel', 'parking', 'toll', 'vehicle', 'bike', 'car'],
        'Education': ['education', 'school', 'college', 'tuition', 'course', 'book', 'books', 'exam', 'fee', 'udemy', 'coursera', 'class', 'classes', 'study', 'semester'],
        'Shopping': ['shopping', 'clothes', 'dress', 'shirt', 'pants', 'shoes', 'amazon', 'flipkart', 'myntra', 'mall', 'store', 'electronics', 'gadget', 'purchase', 'buy'],
        'Entertainment': ['entertainment', 'movie', 'cinema', 'netflix', 'spotify', 'prime', 'game', 'gaming', 'concert', 'event', 'show', 'party', 'youtube', 'subscription'],
        'Healthcare': ['health', 'healthcare', 'doctor', 'hospital', 'clinic', 'medicine', 'pharmacy', 'medical', 'dentist', 'checkup', 'test', 'tablet', 'pills'],
        'Bills & Utilities': ['bill', 'bills', 'utility', 'utilities', 'electricity', 'water', 'wifi', 'internet', 'recharge', 'broadband', 'phone', 'power', 'mobile', 'dth'],
        'Rent & Housing': ['rent', 'house', 'housing', 'flat', 'apartment', 'maintenance', 'room', 'pg', 'mortgage'],
        'Travel': ['travel', 'trip', 'hotel', 'resort', 'vacation', 'tour', 'booking', 'flight ticket', 'train ticket', 'air'],
        'Personal Care': ['personal care', 'salon', 'haircut', 'spa', 'gym', 'fitness', 'beauty', 'cosmetic', 'skincare'],
        'Salary': ['salary', 'wages', 'stipend', 'paycheck', 'payroll', 'monthly pay'],
        'Freelancing': ['freelance', 'freelancing', 'client', 'contract', 'gig', 'consulting', 'project', 'upwork', 'fiverr'],
        'Business': ['business', 'sales', 'profit', 'revenue', 'invoice', 'store sale', 'shop revenue'],
        'Investments': ['investment', 'investments', 'stock', 'stocks', 'dividend', 'crypto', 'mutual fund', 'shares', 'interest', 'trading', 'return', 'fd', 'rd'],
        'Gifts & Grants': ['gift', 'gifts', 'grant', 'bonus', 'reward', 'cashback', 'prize', 'donation', 'scholarship']
    },

    init() {
        this.bindEvents();
    },

    bindEvents() {
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

        const titleInput = document.getElementById('tx-title-input');
        if (titleInput) {
            titleInput.addEventListener('input', (e) => this.autoDetectCategory(e.target.value));
        }

        const txForm = document.getElementById('tx-form');
        if (txForm) {
            txForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.saveTransaction();
            });
        }
    },

    async loadCategories() {
        const res = await API.get('/api/transactions/categories');
        if (res.ok) {
            this.categories = res.data;
            this.populateCategorySelects();
        }
    },

    async ensureCategoriesLoaded() {
        if (!this.categories || this.categories.length === 0) {
            await this.loadCategories();
        }
    },

    populateCategorySelects() {
        const expFilter = document.getElementById('expense-category-filter');
        const incFilter = document.getElementById('income-category-filter');
        const chipsContainer = document.getElementById('tx-category-chips');

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

        const filtered = this.categories.filter(c => c.type === activeType || c.type === 'both');

        if (chipsContainer) {
            chipsContainer.innerHTML = filtered.map(c => `
                <div class="tx-category-chip" data-id="${c.id}" onclick="Finances.selectCategory(${c.id})">
                    <i class="fa-solid ${c.icon}" style="color: ${c.color};"></i>
                    <span>${c.name}</span>
                </div>
            `).join('');
        }
    },

    selectCategory(catId) {
        const hiddenInput = document.getElementById('tx-category-input');
        if (hiddenInput) hiddenInput.value = catId;
        this.highlightCategoryChip(catId);

        const hint = document.getElementById('tx-auto-detect-hint');
        if (hint) hint.style.display = 'none';
    },

    highlightCategoryChip(catId) {
        document.querySelectorAll('.tx-category-chip').forEach(chip => {
            if (chip.dataset.id == catId) {
                chip.classList.add('selected');
            } else {
                chip.classList.remove('selected');
            }
        });
    },

    autoDetectCategory(titleText) {
        if (!titleText || titleText.trim().length < 2) {
            const hint = document.getElementById('tx-auto-detect-hint');
            if (hint) hint.style.display = 'none';
            return;
        }

        const text = titleText.toLowerCase();
        const activeType = document.querySelector('input[name="type"]:checked')?.value || 'expense';
        const filtered = this.categories.filter(c => c.type === activeType || c.type === 'both');

        for (const [catName, keywords] of Object.entries(this.CATEGORY_KEYWORDS)) {
            const matched = keywords.some(kw => text.includes(kw));
            if (matched) {
                const matchedCategory = filtered.find(c => c.name.toLowerCase() === catName.toLowerCase());
                if (matchedCategory) {
                    const hiddenInput = document.getElementById('tx-category-input');
                    if (hiddenInput) hiddenInput.value = matchedCategory.id;
                    this.highlightCategoryChip(matchedCategory.id);

                    const hint = document.getElementById('tx-auto-detect-hint');
                    if (hint) {
                        hint.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Auto-selected: ${matchedCategory.name}`;
                        hint.style.display = 'inline';
                    }
                    return;
                }
            }
        }
    },

    onTypeChange(type) {
        const hiddenInput = document.getElementById('tx-category-input');
        if (hiddenInput) hiddenInput.value = '';
        this.populateCategorySelects();

        const titleInput = document.getElementById('tx-title-input');
        if (titleInput && titleInput.value) {
            this.autoDetectCategory(titleInput.value);
        }
    },

    async loadTransactions(type) {
        if (!Auth.currentUser) return;
        await this.ensureCategoriesLoaded();

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

        if (!res.ok || !res.data || res.data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">No ${type} transactions recorded for this period.</td></tr>`;
            if (totalEl) totalEl.textContent = `${sym} 0.00`;
            if (countEl) countEl.textContent = '0 recorded items';
            return;
        }

        // Safe calculation fallback if summary is ever missing
        let totalAmount = 0;
        if (res.summary) {
            totalAmount = type === 'expense' ? res.summary.total_expense : res.summary.total_income;
        } else {
            totalAmount = res.data.reduce((sum, tx) => sum + (parseFloat(tx.amount) || 0), 0);
        }

        const count = (res.summary && res.summary.count !== undefined) ? res.summary.count : res.data.length;

        if (totalEl) totalEl.textContent = `${sym} ${totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        if (countEl) countEl.textContent = `${count} recorded transactions`;

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
                        ${isInc ? '+' : '-'}${sym} ${(parseFloat(tx.amount) || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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

    async openModal(defaultType = 'expense') {
        if (!Auth.currentUser) {
            Auth.showModal('login');
            return;
        }

        await this.ensureCategoriesLoaded();

        document.getElementById('tx-modal-title').textContent = defaultType === 'income' ? 'Record Income' : 'Record Expense';
        document.getElementById('tx-id-field').value = '';
        document.getElementById('tx-form').reset();
        
        if (defaultType === 'income') {
            document.getElementById('tx-type-income').checked = true;
        } else {
            document.getElementById('tx-type-expense').checked = true;
        }

        document.getElementById('tx-category-input').value = '';
        
        // Use local calendar date without UTC offset shifting
        const now = new Date();
        const localDateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
        document.getElementById('tx-date-input').value = localDateStr;
        document.getElementById('tx-currency-label').textContent = window.CURRENCY_SYMBOL || '₹';
        
        const hint = document.getElementById('tx-auto-detect-hint');
        if (hint) hint.style.display = 'none';

        this.populateCategorySelects();
        document.getElementById('tx-modal').classList.add('active');
    },

    async openEditModal(txId) {
        await this.ensureCategoriesLoaded();

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
        if (tx.category_id) {
            this.selectCategory(tx.category_id);
        }

        const hint = document.getElementById('tx-auto-detect-hint');
        if (hint) hint.style.display = 'none';

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

        if (!category_id) {
            API.showToast('Please select a category by clicking one of the category chips.', 'warning');
            return;
        }

        const payload = {
            type,
            title,
            amount,
            transaction_date,
            category_id: parseInt(category_id),
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

            // Synchronize all workspaces at once
            this.loadTransactions('expense');
            this.loadTransactions('income');
            if (window.Budgets) Budgets.loadBudgets();
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
            if (window.Budgets) Budgets.loadBudgets();
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
