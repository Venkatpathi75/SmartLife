const Notifications = {
    notifications: [],
    unreadCount: 0,

    init() {
        this.bindEvents();
    },

    bindEvents() {
        const bellBtn = document.getElementById('notif-bell-btn');
        const dropdown = document.getElementById('notif-dropdown');

        if (bellBtn && dropdown) {
            bellBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                dropdown.classList.toggle('active');
            });

            // Close on click outside
            document.addEventListener('click', (e) => {
                if (!dropdown.contains(e.target) && e.target !== bellBtn) {
                    dropdown.classList.remove('active');
                }
            });
        }

        const markAllBtn = document.getElementById('notif-mark-all-btn');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', () => this.markAllAsRead());
        }
    },

    async fetchNotifications() {
        if (!Auth.currentUser) return;

        const res = await API.get('/api/notifications');
        if (!res.ok) return;

        this.notifications = res.data.notifications;
        this.unreadCount = res.data.unread_count;

        this.renderBadge();
        this.renderDropdownList();
    },

    renderBadge() {
        const badge = document.getElementById('notif-badge-count');
        if (!badge) return;

        if (this.unreadCount > 0) {
            badge.textContent = this.unreadCount > 9 ? '9+' : this.unreadCount;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    },

    renderDropdownList() {
        const listContainer = document.getElementById('notif-items-list');
        if (!listContainer) return;

        if (this.notifications.length === 0) {
            listContainer.innerHTML = '<p style="text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem;">No notifications right now.</p>';
            return;
        }

        listContainer.innerHTML = this.notifications.map(n => {
            let icon = 'fa-bell';
            let iconColor = 'var(--primary)';

            if (n.type.includes('overdue') || n.type.includes('exceeded')) {
                icon = 'fa-circle-exclamation';
                iconColor = 'var(--danger)';
            } else if (n.type.includes('warning') || n.type.includes('soon')) {
                icon = 'fa-triangle-exclamation';
                iconColor = 'var(--warning)';
            }

            return `
                <div class="notif-item ${n.is_read ? '' : 'unread'}" id="notif-item-${n.id}">
                    <i class="fa-solid ${icon}" style="color: ${iconColor}; margin-top: 0.2rem;"></i>
                    <div class="notif-item-body">
                        <div class="notif-item-title">${n.title}</div>
                        <div class="notif-item-msg">${n.message}</div>
                        <div class="notif-item-time">${n.created_at ? new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}</div>
                    </div>
                    ${!n.is_read ? `
                        <button class="btn-icon-subtle" title="Mark Read" onclick="Notifications.markAsRead(${n.id})">
                            <i class="fa-solid fa-check"></i>
                        </button>` : ''}
                    <button class="btn-icon-subtle delete" title="Dismiss" onclick="Notifications.deleteNotification(${n.id})">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>`;
        }).join('');
    },

    async markAsRead(id) {
        const res = await API.patch(`/api/notifications/${id}/read`, {});
        if (res.ok) {
            await this.fetchNotifications();
        }
    },

    async markAllAsRead() {
        const res = await API.post('/api/notifications/read-all', {});
        if (res.ok) {
            await this.fetchNotifications();
        }
    },

    async deleteNotification(id) {
        const res = await API.delete(`/api/notifications/${id}`);
        if (res.ok) {
            await this.fetchNotifications();
        }
    }
};

window.Notifications = Notifications;
document.addEventListener('DOMContentLoaded', () => Notifications.init());
