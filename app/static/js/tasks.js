const Tasks = {
    currentFilter: '',
    searchDebounce: null,

    init() {
        this.bindEvents();
    },

    bindEvents() {
        const searchInput = document.getElementById('task-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', () => {
                clearTimeout(this.searchDebounce);
                this.searchDebounce = setTimeout(() => this.loadTasks(), 300);
            });
        }

        const priorityFilter = document.getElementById('task-filter-priority');
        if (priorityFilter) {
            priorityFilter.addEventListener('change', () => this.loadTasks());
        }

        const statusFilter = document.getElementById('task-filter-status');
        if (statusFilter) {
            statusFilter.addEventListener('change', () => this.loadTasks());
        }

        document.querySelectorAll('.filter-pill').forEach(pill => {
            pill.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
                e.target.classList.add('active');
                this.currentFilter = e.target.dataset.filter;
                this.loadTasks();
            });
        });

        const form = document.getElementById('task-form');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.saveTask();
            });
        }
    },

    showView(viewName) {
        window.location.hash = `#${viewName}`;
    },

    async loadTasks() {
        if (!Auth.currentUser) {
            const container = document.getElementById('tasks-container');
            if (container) {
                container.innerHTML = `
                    <div class="empty-state-box">
                        <i class="fa-solid fa-lock empty-state-icon"></i>
                        <p>Please <a href="javascript:void(0)" onclick="Auth.showModal('login')">sign in</a> to view and manage your tasks.</p>
                    </div>`;
            }
            return;
        }

        const search = document.getElementById('task-search-input')?.value || '';
        const priority = document.getElementById('task-filter-priority')?.value || 'all';
        const status = document.getElementById('task-filter-status')?.value || 'all';

        let url = `/api/tasks?search=${encodeURIComponent(search)}&priority=${priority}&status=${status}`;
        if (this.currentFilter) {
            url += `&filter_type=${this.currentFilter}`;
        }

        const res = await API.get(url);
        const container = document.getElementById('tasks-container');
        if (!container) return;

        if (!res.ok || res.data.length === 0) {
            container.innerHTML = `
                <div class="empty-state-box">
                    <i class="fa-solid fa-clipboard-check empty-state-icon"></i>
                    <p style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">No tasks found</p>
                    <p style="color: var(--text-muted); margin-bottom: 1.25rem;">Create a new task to stay organized!</p>
                    <button class="btn btn-secondary" onclick="Tasks.openCreateModal()">
                        <i class="fa-solid fa-plus"></i> Create Task
                    </button>
                </div>`;
            return;
        }

        container.innerHTML = res.data.map(task => this.renderTaskCard(task)).join('');
    },

    renderTaskCard(task) {
        const isCompleted = task.status === 'completed';
        const isOverdue = task.due_date && new Date(task.due_date) < new Date() && !isCompleted;
        
        let dueText = 'No due date';
        if (task.due_date) {
            const d = new Date(task.due_date);
            dueText = d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        }

        let checklistHtml = '';
        if (task.checklist_items && task.checklist_items.length > 0) {
            checklistHtml = `
                <div class="checklist-wrapper">
                    ${task.checklist_items.map(item => `
                        <div class="checklist-item-row">
                            <input type="checkbox" ${item.is_completed ? 'checked' : ''} onchange="Tasks.toggleChecklist(${item.id})">
                            <span style="${item.is_completed ? 'text-decoration: line-through; color: var(--text-muted);' : ''}">${item.title}</span>
                        </div>
                    `).join('')}
                </div>`;
        }

        return `
            <div class="task-card-item ${isCompleted ? 'completed' : ''}" id="task-card-${task.id}">
                <input type="checkbox" class="task-checkbox" ${isCompleted ? 'checked' : ''} onchange="Tasks.toggleTaskStatus(${task.id})">
                <div class="task-body">
                    <div class="task-header-row">
                        <span class="task-title-text">${task.title}</span>
                        <span class="badge badge-${task.priority}">${task.priority}</span>
                    </div>
                    ${task.description ? `<p class="task-desc">${task.description}</p>` : ''}
                    <div class="task-meta-bar">
                        <span class="${isOverdue ? 'overdue' : ''}">
                            <i class="fa-regular fa-clock"></i> ${isOverdue ? 'Overdue: ' : ''}${dueText}
                        </span>
                        <span><i class="fa-solid fa-circle-dot"></i> Status: ${task.status}</span>
                    </div>
                    ${checklistHtml}
                </div>
                <div class="task-actions-col">
                    <button class="btn-icon-subtle" title="Edit Task" onclick="Tasks.openEditModal(${task.id})">
                        <i class="fa-solid fa-pen-to-square"></i>
                    </button>
                    <button class="btn-icon-subtle delete" title="Delete Task" onclick="Tasks.deleteTask(${task.id})">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            </div>`;
    },

    async toggleTaskStatus(taskId) {
        const res = await API.patch(`/api/tasks/${taskId}/status`, {});
        if (res.ok) {
            API.showToast(res.message, 'success');
            await this.loadTasks();
            if (window.Dashboard) window.Dashboard.loadDashboard();
            if (window.CalendarApp) window.CalendarApp.refresh();
        }
    },

    async toggleChecklist(itemId) {
        const res = await API.patch(`/api/tasks/checklists/${itemId}/toggle`, {});
        if (res.ok) {
            await this.loadTasks();
        }
    },

    async deleteTask(taskId) {
        if (!confirm('Are you sure you want to delete this task?')) return;

        const res = await API.delete(`/api/tasks/${taskId}`);
        if (res.ok) {
            API.showToast('Task deleted.', 'info');
            await this.loadTasks();
            if (window.Dashboard) window.Dashboard.loadDashboard();
            if (window.CalendarApp) window.CalendarApp.refresh();
        }
    },

    openCreateModal(defaultDate = null) {
        if (!Auth.currentUser) {
            Auth.showModal('login');
            return;
        }

        document.getElementById('task-modal-title').textContent = 'Create New Task';
        document.getElementById('task-id-field').value = '';
        document.getElementById('task-form').reset();
        document.getElementById('checklist-inputs-container').innerHTML = '';

        if (defaultDate) {
            let dt = new Date(defaultDate);
            if (isNaN(dt.getTime())) dt = new Date();
            // Default to 10:00 AM on that day if not time-specific
            if (defaultDate.length <= 10) {
                dt.setHours(10, 0, 0, 0);
            }
            const offset = dt.getTimezoneOffset() * 60000;
            const localISOTime = (new Date(dt - offset)).toISOString().slice(0, 16);
            document.getElementById('task-due-input').value = localISOTime;
        } else {
            document.getElementById('task-due-input').value = '';
        }

        document.getElementById('task-modal').classList.add('active');
    },

    async openEditModal(taskId) {
        const res = await API.get(`/api/tasks/${taskId}`);
        if (!res.ok) return;

        const task = res.data;
        document.getElementById('task-modal-title').textContent = 'Edit Task';
        document.getElementById('task-id-field').value = task.id;
        document.getElementById('task-title-input').value = task.title;
        document.getElementById('task-desc-input').value = task.description || '';
        document.getElementById('task-priority-input').value = task.priority;

        if (task.due_date) {
            const d = new Date(task.due_date);
            const offset = d.getTimezoneOffset() * 60000;
            const localISOTime = (new Date(d - offset)).toISOString().slice(0, 16);
            document.getElementById('task-due-input').value = localISOTime;
        } else {
            document.getElementById('task-due-input').value = '';
        }

        const clContainer = document.getElementById('checklist-inputs-container');
        clContainer.innerHTML = '';
        if (task.checklist_items) {
            task.checklist_items.forEach(item => {
                this.addChecklistInputRow(item.title);
            });
        }

        document.getElementById('task-modal').classList.add('active');
    },

    closeModal() {
        document.getElementById('task-modal').classList.remove('active');
    },

    addChecklistInputRow(val = '') {
        const container = document.getElementById('checklist-inputs-container');
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.gap = '0.5rem';
        row.innerHTML = `
            <input type="text" class="form-input checklist-input-item" value="${val}" placeholder="Subtask title...">
            <button type="button" class="btn btn-outline" style="padding: 0.4rem 0.6rem;" onclick="this.parentElement.remove()">
                <i class="fa-solid fa-xmark"></i>
            </button>`;
        container.appendChild(row);
    },

    async saveTask() {
        const taskId = document.getElementById('task-id-field').value;
        const title = document.getElementById('task-title-input').value.trim();
        const description = document.getElementById('task-desc-input').value;
        const priority = document.getElementById('task-priority-input').value;
        const dueDate = document.getElementById('task-due-input').value;

        const checklistInputs = document.querySelectorAll('.checklist-input-item');
        const checklists = Array.from(checklistInputs).map(i => i.value.trim()).filter(v => v.length > 0);

        const payload = {
            title,
            description,
            priority,
            due_date: dueDate || null,
            checklists
        };

        let res;
        if (taskId) {
            res = await API.put(`/api/tasks/${taskId}`, payload);
        } else {
            res = await API.post('/api/tasks', payload);
        }

        if (res.ok) {
            API.showToast(res.message, 'success');
            this.closeModal();
            await this.loadTasks();
            if (window.Dashboard) window.Dashboard.loadDashboard();
            if (window.CalendarApp) window.CalendarApp.refresh();
        }
    }
};

window.Tasks = Tasks;
document.addEventListener('DOMContentLoaded', () => Tasks.init());
