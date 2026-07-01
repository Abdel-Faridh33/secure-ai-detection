const API_BASE_URL = window.location.port === '8080'
    ? `http://${window.location.hostname}/api/secured`
    : `http://${window.location.hostname}:9800`;

async function authFetch(path, token, options = {}) {
    const headers = { 'Authorization': `Bearer ${token}`, ...(options.headers || {}) };
    return fetch(`${API_BASE_URL}${path}`, { ...options, headers });
}
