/**
 * SmartLife Client Foundation, Sidebar Controller & Dynamic View Router
 */
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSidebar();
    initRouter();
});

function initTheme() {
    const savedTheme = localStorage.getItem('smartlife-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeButton(savedTheme);

    const themeToggleBtn = document.getElementById('theme-toggle');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', nextTheme);
            localStorage.setItem('smartlife-theme', nextTheme);
            updateThemeButton(nextTheme);
            
            if (window.CalendarApp && window.CalendarApp.calendar) {
                window.CalendarApp.calendar.render();
            }
        });
    }
}

function updateThemeButton(theme) {
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (!themeToggleBtn) return;
    
    if (theme === 'dark') {
        themeToggleBtn.innerHTML = '<i class="fa-solid fa-sun"></i> Light Theme';
    } else {
        themeToggleBtn.innerHTML = '<i class="fa-solid fa-moon"></i> Dark Theme';
    }
}

function initSidebar() {
    const toggleBtn = document.getElementById('sidebar-toggle-btn');
    const closeBtn = document.getElementById('sidebar-close-btn');
    const backdrop = document.getElementById('sidebar-backdrop');
    const sidebar = document.getElementById('app-sidebar');

    function closeSidebarMobile() {
        if (sidebar) sidebar.classList.remove('open');
        if (backdrop) backdrop.classList.remove('active');
    }

    function openSidebarMobile() {
        if (sidebar) sidebar.classList.add('open');
        if (backdrop) backdrop.classList.add('active');
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            if (window.innerWidth <= 992) {
                if (sidebar && sidebar.classList.contains('open')) {
                    closeSidebarMobile();
                } else {
                    openSidebarMobile();
                }
            } else {
                document.body.classList.toggle('sidebar-collapsed');
                setTimeout(() => {
                    window.dispatchEvent(new Event('resize'));
                    if (window.CalendarApp && window.CalendarApp.calendar) {
                        window.CalendarApp.calendar.updateSize();
                    }
                }, 200);
            }
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeSidebarMobile);
    }

    if (backdrop) {
        backdrop.addEventListener('click', closeSidebarMobile);
    }

    document.querySelectorAll('.sidebar-nav .nav-link').forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 992) {
                closeSidebarMobile();
            }
        });
    });
}

function initRouter() {
    window.addEventListener('hashchange', handleRoute);
    handleRoute();
}

function handleRoute() {
    const hash = window.location.hash.replace('#', '') || 'dashboard';

    document.querySelectorAll('.app-view').forEach(view => {
        view.style.display = 'none';
    });

    document.querySelectorAll('.sidebar-nav .nav-link').forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        if (href === `#${hash}` || (hash === 'dashboard' && href === '/')) {
            link.classList.add('active');
        }
    });

    const targetView = document.getElementById(`view-${hash}`);
    if (targetView) {
        targetView.style.display = 'block';
    } else {
        const dashboardView = document.getElementById('view-dashboard');
        if (dashboardView) dashboardView.style.display = 'block';
    }

    // Module loaders
    if (hash === 'tasks' && window.Tasks) {
        window.Tasks.loadTasks();
    } else if (hash === 'calendar' && window.CalendarApp) {
        window.CalendarApp.initOrRefresh();
    } else if (hash === 'expenses' && window.Finances) {
        window.Finances.loadTransactions('expense');
    } else if (hash === 'income' && window.Finances) {
        window.Finances.loadTransactions('income');
    } else if (hash === 'budgets' && window.Budgets) {
        window.Budgets.loadBudgets();
    } else if (hash === 'reports' && window.Reports) {
        window.Reports.loadReports();
    } else if (hash === 'admin' && window.Admin) {
        window.Admin.loadDashboard();
    } else if (hash === 'dashboard' && window.Dashboard) {
        window.Dashboard.loadDashboard();
    }

    if (window.Notifications && Auth.currentUser) {
        window.Notifications.fetchNotifications();
    }
}
