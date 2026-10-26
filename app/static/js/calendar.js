const CalendarApp = {
    calendar: null,

    initOrRefresh() {
        if (!Auth.currentUser) {
            const root = document.getElementById('calendar-root');
            if (root) {
                root.innerHTML = `
                    <div class="empty-state-box">
                        <i class="fa-solid fa-lock empty-state-icon"></i>
                        <p>Please <a href="javascript:void(0)" onclick="Auth.showModal('login')">sign in</a> to view your calendar schedule.</p>
                    </div>`;
            }
            return;
        }

        const calendarEl = document.getElementById('calendar-root');
        if (!calendarEl) return;

        if (!this.calendar) {
            this.initCalendar(calendarEl);
        } else {
            this.calendar.render();
            this.calendar.refetchEvents();
        }
    },

    initCalendar(calendarEl) {
        this.calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay,listMonth'
            },
            editable: true,
            navLinks: true,
            dayMaxEvents: true,
            eventTimeFormat: {
                hour: 'numeric',
                minute: '2-digit',
                meridiem: 'short'
            },
            // Dynamic event provider connecting to /api/calendar/events
            events: async (fetchInfo, successCallback, failureCallback) => {
                const showTasks = document.getElementById('cal-filter-tasks')?.checked ?? true;
                const showFinances = document.getElementById('cal-filter-finances')?.checked ?? true;

                const url = `/api/calendar/events?start=${encodeURIComponent(fetchInfo.startStr)}&end=${encodeURIComponent(fetchInfo.endStr)}&show_tasks=${showTasks}&show_finances=${showFinances}`;
                const res = await API.get(url);

                if (res.ok) {
                    successCallback(res.data);
                } else {
                    failureCallback(res.error);
                }
            },
            // Click on date slot -> opens Task Create Modal with that date pre-filled
            dateClick: (info) => {
                Tasks.openCreateModal(info.dateStr);
            },
            // Click on event -> opens task edit modal or detail toast
            eventClick: (info) => {
                const props = info.event.extendedProps;
                if (props.eventType === 'task') {
                    Tasks.openEditModal(info.event.extendedProps.taskId || info.event.id.replace('task_', ''));
                } else if (props.eventType === 'transaction') {
                    API.showToast(`${info.event.title} (${props.category})`, 'info');
                }
            },
            // Drag-and-drop rescheduling
            eventDrop: async (info) => {
                const props = info.event.extendedProps;
                if (props.eventType !== 'task') {
                    info.revert();
                    API.showToast('Only tasks can be rescheduled by drag and drop.', 'warning');
                    return;
                }

                const taskId = info.event.extendedProps.taskId || info.event.id.replace('task_', '');
                const newDate = info.event.start.toISOString();

                const res = await API.patch(`/api/calendar/events/${taskId}/reschedule`, {
                    new_date: newDate
                });

                if (res.ok) {
                    API.showToast(res.message, 'success');
                    if (window.Tasks) Tasks.loadTasks();
                    if (window.Dashboard) Dashboard.loadDashboard();
                } else {
                    info.revert();
                }
            }
        });

        this.calendar.render();
    },

    refresh() {
        if (this.calendar) {
            this.calendar.refetchEvents();
        }
    }
};

window.CalendarApp = CalendarApp;
