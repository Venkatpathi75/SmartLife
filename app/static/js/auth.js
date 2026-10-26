const Auth = {
    currentUser: null,

    async init() {
        const res = await API.get('/api/auth/me');
        if (res.ok && res.data.authenticated) {
            this.currentUser = res.data.user;
            this.updateUIForUser(res.data.user);
            if (window.Dashboard) {
                window.Dashboard.loadDashboard();
            }
            if (window.Finances) {
                window.Finances.loadCategories();
            }
        } else {
            this.updateUIForGuest();
        }

        this.bindEvents();
    },

    bindEvents() {
        const openLoginBtns = document.querySelectorAll('.open-login-btn');
        openLoginBtns.forEach(btn => btn.addEventListener('click', () => this.showModal('login')));

        const modalCloseBtn = document.getElementById('auth-modal-close');
        if (modalCloseBtn) modalCloseBtn.addEventListener('click', () => this.hideModal());

        const authTabs = document.querySelectorAll('.auth-tab');
        authTabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const target = e.target.dataset.tab;
                this.switchTab(target);
            });
        });

        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.handleLogin(new FormData(loginForm));
            });
        }

        const registerForm = document.getElementById('register-form');
        if (registerForm) {
            registerForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.handleRegister(new FormData(registerForm));
            });
        }

        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.handleLogout();
            });
        }
    },

    showModal(tab = 'login') {
        const modal = document.getElementById('auth-modal');
        if (modal) {
            modal.classList.add('active');
            this.switchTab(tab);
        }
    },

    hideModal() {
        const modal = document.getElementById('auth-modal');
        if (modal) modal.classList.remove('active');
    },

    switchTab(tab) {
        document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.auth-panel').forEach(p => p.style.display = 'none');

        const activeTab = document.querySelector(`[data-tab="${tab}"]`);
        const activePanel = document.getElementById(`${tab}-panel`);

        if (activeTab) activeTab.classList.add('active');
        if (activePanel) activePanel.style.display = 'block';
    },

    async handleLogin(formData) {
        const payload = Object.fromEntries(formData.entries());
        const res = await API.post('/api/auth/login', payload);

        if (res.ok) {
            API.showToast(res.message, 'success');
            this.currentUser = res.data.user;
            this.updateUIForUser(res.data.user);
            this.hideModal();
            if (window.Dashboard) {
                window.Dashboard.loadDashboard();
            }
            if (window.Finances) {
                window.Finances.loadCategories();
            }
        }
    },

    async handleRegister(formData) {
        const payload = Object.fromEntries(formData.entries());
        const res = await API.post('/api/auth/register', payload);

        if (res.ok) {
            API.showToast('Account created! Logging you in...', 'success');
            await this.handleLogin(formData);
        }
    },

    async handleLogout() {
        const res = await API.post('/api/auth/logout', {});
        if (res.ok) {
            API.showToast('Signed out successfully.', 'info');
            this.currentUser = null;
            this.updateUIForGuest();
            window.location.reload();
        }
    },

    updateUIForUser(user) {
        document.querySelectorAll('.user-authenticated').forEach(el => el.style.display = 'flex');
        document.querySelectorAll('.user-guest').forEach(el => el.style.display = 'none');
        
        const nameEl = document.getElementById('user-display-name');
        if (nameEl) nameEl.textContent = user.name;

        const currencySymbol = user.currency === 'INR' ? '₹' : (user.currency === 'USD' ? '$' : user.currency);
        window.CURRENCY_SYMBOL = currencySymbol;

        const adminNav = document.getElementById('admin-nav-item');
        if (adminNav) {
            adminNav.style.display = user.role === 'admin' ? 'block' : 'none';
        }
    },

    updateUIForGuest() {
        document.querySelectorAll('.user-authenticated').forEach(el => el.style.display = 'none');
        document.querySelectorAll('.user-guest').forEach(el => el.style.display = 'flex');
        
        const adminNav = document.getElementById('admin-nav-item');
        if (adminNav) adminNav.style.display = 'none';
    }
};

window.Auth = Auth;
document.addEventListener('DOMContentLoaded', () => Auth.init());
