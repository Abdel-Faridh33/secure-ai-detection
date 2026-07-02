// Détection automatique de l'environnement selon le port d'accès
// - 8443 : prod HTTPS  → API nginx prod (https://host)
// - 8800 : dev         → API dev directe (http://host:9800)
// - 9800 : API directe → API dev directe
const _port = window.location.port;
const _host = window.location.hostname;
const API_BASE_URL =
    _port === '8443' ? `https://${_host}`
    : _port === '8800' ? `http://${_host}:9800`
    : `http://${_host}:9800`;

async function authFetch(path, token, options = {}) {
    const headers = { 'Authorization': `Bearer ${token}`, ...(options.headers || {}) };
    return fetch(`${API_BASE_URL}${path}`, { ...options, headers });
}
