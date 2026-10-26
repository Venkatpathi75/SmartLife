const Admin = {
    searchDebounce: null,

    init() {
        this.bindEvents();
    },

    bindEvents() {
        const searchInput = document.getElementById('admin-user-search');
        if (searchInput) {
            searchInput.addEventListener('input', () => {
                clearTimeout(this.searchDebounce);
                this.searchDebounce = setTimeout(() => this.fetchUsers(), 300);
            });
        }

        document.getElementById('admin-user-status')?.addEventListener('change', () => this.fetchUsers());
        document.getElementById('admin-user-role')?.addEventListener('change', () => this.fetchUsers());
    },

    async loadDashboard() {
        if (!Auth.currentUser || Auth.currentUser.role !== 'admin') {
            API.showToast('Administrator privileges required.', 'error');
            window.location.hash = '#dashboard';
            return;
        }

        await Promise.all([
            this.fetchStats(),
            this.fetchUsers(),
            this.fetchAuditLogs()
        ]);
    },

    async fetchStats() {
        const res = await API.get('/api/admin/stats');
        if (!res.ok) return;

        const data = res.data;
        const sym = window.CURRENCY_SYMBOL || '₹';

        document.getElementById('admin-stat-users').textContent = data.users.total;
        document.getElementById('admin-stat-active').textContent = data.users.active;
        document.getElementById('admin-stat-inactive').textContent = data.users.inactive;
        document.getElementById('admin-stat-volume').textContent = `${sym} ${data.finances.total_volume.toLocaleString()}`;
    },

    async fetchUsers() {
        const search = document.getElementById('admin-user-search')?.value || '';
        const status = document.getElementById('admin-user-status')?.value || 'all';
        const role = document.getElementById('admin-user-role')?.value || 'all';

        const url = `/api/admin/users?search=${encodeURIComponent(search)}&status=${status}&role=${role}`;
        const res = await API.get(url);
        const tbody = document.getElementById('admin-users-table-body');
        if (!tbody) return;

        if (!res.ok || res.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">No users match the criteria.</td></tr>';
            return;
        }

        tbody.innerHTML = res.data.map(u => {
            const isSelf = u.id === Auth.currentUser.id;
            const statusBadge = u.is_active 
                ? '<span class="badge" style="background-color: var(--success-light); color: var(--success);">Active</span>'
                : '<span class="badge" style="background-color: var(--danger-light); color: var(--danger);">Suspended</span>';

            const roleBadge = u.role === 'admin'
                ? '<span class="badge" style="background-color: var(--primary-light); color: var(--primary); font-weight: 700;">Admin</span>'
                : '<span class="badge" style="background-color: var(--bg-page); color: var(--text-muted);">User</span>';

            return `
                <tr>
                    <td>
                        <div style="font-weight: 600; color: var(--text-main);">${u.name} ${isSelf ? '<small style="color: var(--primary);">(You)</small>' : ''}</div>
                        <div style="font-size: 0.8rem; color: var(--text-muted);">${u.email}</div>
                    </td>
                    <td>${roleBadge}</td>
                    <td>${statusBadge}</td>
                    <td style="font-size: 0.825rem; color: var(--text-muted);">${u.created_at || 'N/A'}</td>
                    <td style="font-size: 0.825rem;">
                        <span><i class="fa-solid fa-list-check"></i> ${u.task_count} tasks</span> &bull; 
                        <span><i class="fa-solid fa-receipt"></i> ${u.transaction_count} txs</span>
                    </td>
                    <td style="text-align: right;">
                        ${isSelf ? '<span style="font-size: 0.8rem; color: var(--text-subtle);">Protected</span>' : `
                            <button class="btn btn-outline" style="font-size: 0.775rem; padding: 0.35rem 0.65rem; color: ${u.is_active ? 'var(--danger)' : 'var(--success)'};" 
                                onclick="Admin.toggleUserStatus(${u.id}, '${u.email}', ${u.is_active})">
                                <i class="fa-solid ${u.is_active ? 'fa-user-slash' : 'fa-user-check'}"></i> ${u.is_active ? 'Suspend' : 'Activate'}
                            </button>
                        `}
                    </td>
                </tr>`;
        }).join('');
    },

    async toggleUserStatus(userId, email, currentStatus) {
        const actionVerb = currentStatus ? 'suspend' : 'activate';
        if (!confirm(`Are you sure you want to ${actionVerb} access for user ${email}?`)) return;

        const res = await API.patch(`/api/admin/users/${userId}/status`, {});
        if (res.ok) {
            API.showToast(res.message, 'success');
            await Promise.all([
                this.fetchStats(),
                this.fetchUsers(),
                this.fetchAuditLogs()
            ]);
        }
    },

    async fetchAuditLogs() {
        const res = await API.get('/api/admin/audit-logs');
        const tbody = document.getElementById('admin-audit-table-body');
        if (!tbody) return;

        if (!res.ok || res.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">No administrative events recorded yet.</td></tr>';
            return;
        }

        tbody.innerHTML = res.data.map(l => `
            <tr>
                <td style="font-size: 0.8rem; color: var(--text-muted);">${l.created_at}</td>
                <td style="font-weight: 500;">${l.actor_name}</td>
                <td><span class="badge" style="background-color: var(--primary-light); color: var(--primary); font-family: monospace;">${l.action}</span></td>
                <td style="font-size: 0.825rem;">${l.target_type || '-'} #${l.target_id || '-'}</td>
                <td style="font-size: 0.8rem; font-family: monospace; color: var(--text-subtle);">${l.ip_address || '127.0.0.1'}</td>
                <td style="font-size: 0.825rem; color: var(--text-muted);">${l.details || '-'}</td>
            </tr>
        `).join('');
    }
};

window.Admin = Admin;
document.addEventListener('DOMContentLoaded', () => Admin.init());
