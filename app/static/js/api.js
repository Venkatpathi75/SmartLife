const API = {
    csrfToken: null,

    getCsrfToken() {
        if (!this.csrfToken) {
            const meta = document.querySelector('meta[name="csrf-token"]');
            this.csrfToken = meta ? meta.getAttribute('content') : '';
        }
        return this.csrfToken;
    },

    async request(url, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCsrfToken(),
            ...(options.headers || {})
        };

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                const message = data.error?.message || 'A network error occurred.';
                this.showToast(message, 'error');
                return { ok: false, status: response.status, error: data.error };
            }

            // Preserves data, summary, message, and all top-level server response fields
            return {
                ok: true,
                status: response.status,
                ...data,
                data: data.data !== undefined ? data.data : data
            };
        } catch (err) {
            this.showToast('Server connection failed.', 'error');
            return { ok: false, status: 500, error: { message: err.message } };
        }
    },

    get(url) {
        return this.request(url, { method: 'GET' });
    },

    post(url, body) {
        return this.request(url, { method: 'POST', body: JSON.stringify(body) });
    },

    put(url, body) {
        return this.request(url, { method: 'PUT', body: JSON.stringify(body) });
    },

    patch(url, body) {
        return this.request(url, { method: 'PATCH', body: JSON.stringify(body) });
    },

    delete(url) {
        return this.request(url, { method: 'DELETE' });
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let icon = 'fa-info-circle';
        if (type === 'success') icon = 'fa-check-circle';
        if (type === 'error') icon = 'fa-circle-exclamation';
        if (type === 'warning') icon = 'fa-triangle-exclamation';

        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 200);
        }, 4000);
    }
};

window.API = API;
