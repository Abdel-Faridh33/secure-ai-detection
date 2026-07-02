let adminToken     = null;
let currentRole    = null;
let wafRateLimit   = 50;
let wafRefreshInterval = null;

// =============================================
// TAB NAVIGATION
// =============================================

function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.closest('.tab').classList.add('active');
    if (tabName === 'overview')  { loadOverviewStats(); loadWAFStatus(); }
    if (tabName === 'audit')     loadAuditLogs();
    if (tabName === 'detection') loadDetectionStats();
    if (tabName === 'system')    loadSystemMetrics();
}

// =============================================
// USERS – liste + création
// =============================================

function openCreateUserModal() {
    document.getElementById('newUsername').value = '';
    document.getElementById('newEmail').value    = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('newRole').value     = 'guest';
    document.getElementById('modalError').classList.remove('show');
    document.getElementById('modalError').textContent = '';
    document.getElementById('createUserBackdrop').classList.add('open');
    document.getElementById('createUserModal').classList.add('open');
    document.getElementById('newUsername').focus();
}

function closeCreateUserModal() {
    document.getElementById('createUserBackdrop').classList.remove('open');
    document.getElementById('createUserModal').classList.remove('open');
}

async function submitCreateUser() {
    const username = document.getElementById('newUsername').value.trim();
    const email    = document.getElementById('newEmail').value.trim();
    const password = document.getElementById('newPassword').value;
    const role     = document.getElementById('newRole').value;
    const errEl    = document.getElementById('modalError');
    const btn      = document.getElementById('createUserBtn');

    errEl.classList.remove('show');

    if (!username || username.length < 3) {
        errEl.textContent = 'Nom d\'utilisateur trop court (min 3 caractères).';
        errEl.classList.add('show');
        return;
    }
    if (!email || !email.includes('@')) {
        errEl.textContent = 'Adresse email invalide.';
        errEl.classList.add('show');
        return;
    }
    if (!password || password.length < 6) {
        errEl.textContent = 'Mot de passe trop court (min 6 caractères).';
        errEl.classList.add('show');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Création...';

    try {
        const res = await authFetch('/security/users', adminToken, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password, role })
        });
        const data = await res.json();
        if (!res.ok) {
            errEl.textContent = data.detail || 'Erreur lors de la création.';
            errEl.classList.add('show');
            return;
        }
        closeCreateUserModal();
        loadUsers();
    } catch {
        errEl.textContent = 'Impossible de joindre le serveur.';
        errEl.classList.add('show');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Créer l\'utilisateur';
    }
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeCreateUserModal();
});


async function loadUsers() {
    try {
        const res = await authFetch('/security/users', adminToken);
        if (!res.ok) throw new Error();
        const users = await res.json();
        displayUsers(users);
        updateStats(users);
    } catch {
        document.getElementById('loadingDiv').innerHTML =
            '<p style="color:var(--danger);padding:1rem">Erreur de chargement des utilisateurs</p>';
    }
}

function displayUsers(users) {
    const protected_ = ['admin', 'agent1'];
    const fmtDate = iso => iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—';
    document.getElementById('usersBody').innerHTML = users.map(u => `
        <tr>
            <td>${u.username}</td>
            <td>${u.email || '—'}</td>
            <td><span class="role-badge role-${u.role}">${u.role}</span></td>
            <td style="color:var(--text-muted);font-size:.85rem">${fmtDate(u.created_at)}</td>
            <td style="color:var(--text-muted);font-size:.85rem">${fmtDate(u.last_login)}</td>
            <td>${protected_.includes(u.username)
                ? '<button class="btn btn-danger btn-sm" disabled>Protégé</button>'
                : `<button class="btn btn-danger btn-sm" onclick="deleteUser('${u.username}')">Supprimer</button>`
            }</td>
        </tr>`).join('');
    document.getElementById('loadingDiv').style.display = 'none';
    document.getElementById('usersTableWrap').style.display = 'block';
}

function updateStats(users) {
    document.getElementById('totalUsers').textContent  = users.length;
    document.getElementById('totalAdmins').textContent = users.filter(u => u.role === 'admin').length;
    document.getElementById('totalAgents').textContent = users.filter(u => u.role === 'agent').length;
    document.getElementById('totalGuests').textContent = users.filter(u => u.role === 'guest').length;
}

async function deleteUser(username) {
    if (!confirm(`Supprimer l'utilisateur « ${username} » ?`)) return;
    try {
        const res = await authFetch(`/security/users/${username}`, adminToken, { method: 'DELETE' });
        if (!res.ok) throw new Error();
        alert('Utilisateur supprimé.');
        loadUsers();
    } catch {
        alert('Erreur lors de la suppression.');
    }
}

// =============================================
// AUDIT LOGS – couleurs, badges, pagination
// =============================================

const EVENT_META = {
    prediction:       { label: 'Prédiction',         bg: '#eff6ff', color: '#1d4ed8', dot: '#3b82f6' },
    attack_detected:  { label: 'Attaque détectée',   bg: '#fef2f2', color: '#991b1b', dot: '#ef4444' },
    security_block:   { label: 'Blocage WAF',         bg: '#fff7ed', color: '#9a3412', dot: '#f97316' },
    anomaly_critical: { label: 'Anomalie critique',   bg: '#fdf4ff', color: '#7e22ce', dot: '#a855f7' },
    anomaly_detected: { label: 'Anomalie',            bg: '#fdf4ff', color: '#7e22ce', dot: '#c084fc' },
    login_success:    { label: 'Connexion réussie',   bg: '#f0fdf4', color: '#166534', dot: '#22c55e' },
    login_failed:     { label: 'Échec connexion',     bg: '#fef2f2', color: '#991b1b', dot: '#fca5a5' },
    api_access:       { label: 'Accès API',           bg: '#f8fafc', color: '#475569', dot: '#94a3b8' },
    security_check:   { label: 'Vérification sécurité', bg: '#f0fdfa', color: '#134e4a', dot: '#14b8a6' },
    system_error:     { label: 'Erreur système',      bg: '#fdf2f8', color: '#831843', dot: '#ec4899' },
    model_loaded:     { label: 'Modèle chargé',       bg: '#f0f9ff', color: '#0c4a6e', dot: '#0ea5e9' },
    validation_failed:{ label: 'Validation échouée',  bg: '#fffbeb', color: '#92400e', dot: '#f59e0b' },
};

const SEVERITY_LABEL = { info: 'Info', warning: 'Avert.', critical: 'Critique', security_alert: 'Alerte' };

let allAuditLogs = [];
let auditCurrentPage = 0;
const AUDIT_PAGE_SIZE = 5;

async function loadAuditLogs() {
    const container = document.getElementById('auditLogs');
    container.innerHTML = '<div class="loading show"><div class="spinner spinner-lg"></div><p>Chargement des journaux...</p></div>';
    try {
        const res = await authFetch('/audit/logs?limit=100', adminToken);
        if (!res.ok) throw new Error();
        allAuditLogs = (await res.json()).logs || [];
        auditCurrentPage = 0;
        renderAuditPage();
    } catch {
        container.innerHTML = '<p style="color:var(--danger);padding:1rem">Erreur de chargement des journaux d\'audit</p>';
    }
}

function changeAuditPage(delta) {
    const totalPages = Math.ceil(allAuditLogs.length / AUDIT_PAGE_SIZE);
    auditCurrentPage = Math.max(0, Math.min(auditCurrentPage + delta, totalPages - 1));
    renderAuditPage();
}

function renderAuditPage() {
    const container = document.getElementById('auditLogs');
    const totalPages = Math.max(1, Math.ceil(allAuditLogs.length / AUDIT_PAGE_SIZE));
    const start = auditCurrentPage * AUDIT_PAGE_SIZE;
    const pageLogs = allAuditLogs.slice(start, start + AUDIT_PAGE_SIZE);

    // Toujours construire le HTML des logs (vide ou non)
    const emptyHtml = '<p style="color:var(--text-secondary);text-align:center;padding:2rem 1rem">Aucun journal disponible</p>';

    const logsHtml = pageLogs.length === 0 ? emptyHtml : pageLogs.map(log => {
        const severity = log.severity || 'info';
        const cls      = (severity === 'critical' || severity === 'security_alert') ? 'critical'
                       : severity === 'warning' ? 'warning' : '';

        const meta     = EVENT_META[log.event_type] || { label: log.event_type || 'Événement', bg: '#f8fafc', color: '#475569', dot: '#94a3b8' };
        const ts       = new Date(log.timestamp).toLocaleString('fr-FR');
        const clientIp = log.user?.client_ip || log.ip_address || 'N/A';
        const userRole = log.user?.user_role || '';
        const sevLabel = SEVERITY_LABEL[severity] || severity;

        let details = '';
        if (log.event_type === 'prediction' && log.prediction) {
            const res = log.prediction.result === 'safe'
                ? '<span style="color:#059669;font-weight:600">Sûr</span>'
                : '<span style="color:#dc2626;font-weight:600">Dangereux</span>';
            details = `Modèle : ${log.prediction.model_type} · Verdict : ${res} · Confiance : ${(log.prediction.confidence * 100).toFixed(1)} % · Durée : ${log.prediction.processing_time_ms.toFixed(0)} ms`;
            if (log.image) details += ` · Fichier : <code style="font-size:.75rem">${log.image.filename}</code>`;
        } else if (log.event_type === 'api_access' && log.api) {
            const sc = log.api.status_code;
            const scColor = sc >= 500 ? '#dc2626' : sc >= 400 ? '#d97706' : '#059669';
            details = `${log.api.method} <code style="font-size:.75rem">${log.api.endpoint}</code> · Statut : <strong style="color:${scColor}">${sc}</strong> · Durée : ${(log.api.response_time_ms || 0).toFixed(0)} ms`;
        } else if (log.details || log.description) {
            details = log.details || log.description;
        }

        return `
            <div class="audit-log-item ${cls}">
                <div class="audit-log-header">
                    <div class="audit-log-left">
                        <span class="audit-badge" style="background:${meta.bg};color:${meta.color}">
                            <span class="audit-badge-dot" style="background:${meta.dot}"></span>
                            ${meta.label}
                        </span>
                        <span class="audit-severity">${sevLabel}</span>
                    </div>
                    <span class="audit-log-time">${ts}</span>
                </div>
                <div class="audit-log-meta">
                    <span>IP : <strong>${clientIp}</strong></span>
                    ${userRole ? `<span>Rôle : <strong>${userRole}</strong></span>` : ''}
                    <span>ID : <code style="font-size:.7rem">${log.audit_id || 'N/A'}</code></span>
                </div>
                ${details ? `<div class="audit-log-details">${details}</div>` : ''}
            </div>`;
    }).join('');

    const paginationHtml = `
        <div class="pagination">
            <button class="page-btn" onclick="changeAuditPage(-1)" ${auditCurrentPage === 0 ? 'disabled' : ''}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><polyline points="15 18 9 12 15 6"/></svg>
                Précédent
            </button>
            <span class="page-info">
                Page <strong>${auditCurrentPage + 1}</strong> / <strong>${Math.max(1, totalPages)}</strong>
                &nbsp;·&nbsp; ${allAuditLogs.length} entrée${allAuditLogs.length !== 1 ? 's' : ''}
            </span>
            <button class="page-btn" onclick="changeAuditPage(1)" ${auditCurrentPage >= totalPages - 1 ? 'disabled' : ''}>
                Suivant
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
        </div>`;

    container.innerHTML = logsHtml + paginationHtml;
}

// =============================================
// DETECTION STATS
// =============================================

async function loadDetectionStats() {
    const container = document.getElementById('detectionStats');
    container.innerHTML = '<div class="loading show"><div class="spinner spinner-lg"></div><p>Chargement...</p></div>';
    try {
        const res = await authFetch('/security/detection/stats', adminToken);
        if (!res.ok) throw new Error();
        displayDetectionStats(await res.json());
    } catch {
        container.innerHTML = '<p style="color:var(--danger);padding:1rem">Erreur de chargement des statistiques</p>';
    }
}

function displayDetectionStats(stats) {
    const cleanAcc  = (stats.accuracy_clean || 0).toFixed(2);
    const fgsmRob   = (stats.fgsm_robustness || (100 - (stats.fgsm_attack_success_rate || 0))).toFixed(2);
    const asrRed    = ((stats.reference_fgsm_asr || 0) - (stats.fgsm_attack_success_rate || 0)).toFixed(2);

    document.getElementById('securedAccuracy').textContent = `${cleanAcc} %`;
    document.getElementById('fgsmRobustness').textContent  = `${fgsmRob} %`;
    document.getElementById('asrReduction').textContent    = `${asrRed} %`;

    const refAcc     = stats.reference_accuracy_clean != null ? `${stats.reference_accuracy_clean.toFixed(1)} %` : 'N/A';
    const refFgsm    = stats.reference_fgsm_asr != null ? `${stats.reference_fgsm_asr.toFixed(1)} %` : 'N/A';
    const secFgsm    = (stats.fgsm_attack_success_rate || 0).toFixed(2);
    const diffAcc    = stats.reference_accuracy_clean != null
        ? `+${((stats.accuracy_clean || 0) - stats.reference_accuracy_clean).toFixed(2)} %` : 'N/A';
    const diffFgsm   = stats.reference_fgsm_asr != null
        ? `-${(stats.reference_fgsm_asr - (stats.fgsm_attack_success_rate || 0)).toFixed(2)} %` : 'N/A';
    const refFgsmRob = stats.reference_fgsm_asr != null
        ? `${(100 - stats.reference_fgsm_asr).toFixed(1)} %` : 'N/A';
    const diffFgsmRob = stats.reference_fgsm_asr != null
        ? `+${(parseFloat(fgsmRob) - (100 - stats.reference_fgsm_asr)).toFixed(2)} %` : 'N/A';

    document.getElementById('detectionStats').innerHTML = `
        <div class="stats-table-card">
            <div class="stats-table-card-header">
                <h3>Robustesse adversariale – FGSM (ε = 0,08)</h3>
                <p class="stats-source">Source : <code>${stats.data_source || 'N/A'}</code> — Architecture : ${stats.architecture || 'N/A'}</p>
            </div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Métrique</th>
                            <th>Référence (non sécurisé)</th>
                            <th>Sécurisé (MobileNetV2)</th>
                            <th>Amélioration</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td><strong>Précision (données nettes)</strong></td><td>${refAcc}</td><td>${cleanAcc} %</td><td class="improvement">${diffAcc}</td></tr>
                        <tr><td><strong>ASR – FGSM</strong></td><td>${refFgsm}</td><td>${secFgsm} %</td><td class="improvement">${diffFgsm}</td></tr>
                        <tr><td><strong>Robustesse FGSM</strong></td><td>${refFgsmRob}</td><td>${fgsmRob} %</td><td class="improvement">${diffFgsmRob}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>`;
}

// =============================================
// SYSTEM METRICS
// =============================================

async function loadSystemMetrics() {
    try {
        const res = await authFetch('/security/system/metrics', adminToken);
        if (!res.ok) throw new Error();
        displaySystemMetrics(await res.json());
    } catch {
        ['cpuUsage', 'memoryUsage', 'requestRate', 'uptime'].forEach(id =>
            document.getElementById(id).textContent = 'Erreur'
        );
    }
}

function displaySystemMetrics(m) {
    const cpu = m.cpu_usage;
    const mem = m.memory_usage;

    if (cpu != null) {
        document.getElementById('cpuUsage').textContent = `${cpu.toFixed(1)} %`;
        document.getElementById('cpuProgress').style.width = `${cpu}%`;
    } else {
        document.getElementById('cpuUsage').textContent = 'N/A';
        document.getElementById('cpuProgress').style.width = '0%';
    }

    if (mem != null) {
        document.getElementById('memoryUsage').textContent = `${mem.toFixed(1)} %`;
        document.getElementById('memoryProgress').style.width = `${mem}%`;
    } else {
        document.getElementById('memoryUsage').textContent = 'N/A';
        document.getElementById('memoryProgress').style.width = '0%';
    }

    document.getElementById('requestRate').textContent = m.request_rate || 0;
    const h   = Math.floor(m.uptime_hours || 0);
    const min = Math.floor(((m.uptime_hours || 0) - h) * 60);
    document.getElementById('uptime').textContent = h > 0 ? `${h} h ${min} min` : `${min} min`;
}

// =============================================
// OVERVIEW STATS
// =============================================

async function loadOverviewStats() {
    try {
        const res = await authFetch('/security/detection/totals', adminToken);
        if (!res.ok) return;
        const d = await res.json();
        document.getElementById('totalDetections').textContent     = d.total || 0;
        document.getElementById('dangerousDetections').textContent = d.dangerous || 0;
        document.getElementById('attacksBlocked').textContent      = d.attacks_blocked || 0;
    } catch {}
}

// =============================================
// WAF
// =============================================

async function loadWAFStatus() {
    try {
        const [statusRes, blockedRes] = await Promise.all([
            fetch(`${API_BASE_URL}/security/waf/status`),
            authFetch('/security/waf/blocked-ips', adminToken)
        ]);
        const status  = statusRes.ok  ? await statusRes.json()  : null;
        const blocked = blockedRes.ok ? await blockedRes.json() :
            { count: 0, blocked_ips: [], rate_limit: '?', window_seconds: 60 };

        const rateLimit    = blocked.rate_limit || (status?.max_requests ?? '?');
        const windowSec    = blocked.window_seconds || (status?.window_seconds ?? 60);
        const currentCount = status?.current_request_count ?? 0;
        const isBlocked    = status?.is_blocked ?? false;
        const pct          = rateLimit > 0 ? Math.min(100, Math.round(currentCount / rateLimit * 100)) : 0;
        const barColor     = pct > 80 ? 'var(--danger)' : pct > 50 ? 'var(--warning)' : 'var(--success)';
        const statusColor  = isBlocked ? 'var(--danger)' : 'var(--success)';
        const statusText   = isBlocked ? 'BLOQUÉE' : 'Autorisée';

        const blockedRows = (blocked.blocked_ips || []).map(b => `
            <tr>
                <td>${b.ip}</td>
                <td>${new Date(b.blocked_until).toLocaleTimeString('fr-FR')}</td>
                <td>${b.remaining_seconds} s</td>
            </tr>`).join('');

        document.getElementById('wafSection').innerHTML = `
            <div class="waf-grid">
                <div class="waf-card">
                    <div class="waf-card-label">Limite de taux</div>
                    <div class="waf-card-value">${rateLimit} req / ${windowSec} s</div>
                </div>
                <div class="waf-card">
                    <div class="waf-card-label">Requêtes (votre IP)</div>
                    <div class="waf-card-value" style="color:${barColor}">${currentCount} / ${rateLimit}</div>
                    <div class="waf-bar-bg">
                        <div class="waf-bar-fill" style="width:${pct}%;background:${barColor}"></div>
                    </div>
                </div>
                <div class="waf-card">
                    <div class="waf-card-label">Statut votre IP</div>
                    <div class="waf-card-value" style="color:${statusColor};font-size:1.2rem">${statusText}</div>
                </div>
                <div class="waf-card">
                    <div class="waf-card-label">IPs bloquées</div>
                    <div class="waf-card-value" style="color:${blocked.count > 0 ? 'var(--danger)' : 'var(--text)'}">
                        ${blocked.count}
                    </div>
                </div>
            </div>
            ${blocked.count > 0 ? `
            <div class="waf-card" style="margin-top:.5rem">
                <h4 class="waf-blocked-title" style="margin-bottom:.75rem">IPs bloquées par le WAF</h4>
                <div class="table-wrap">
                    <table>
                        <thead><tr><th>Adresse IP</th><th>Bloquée jusqu'à</th><th>Temps restant</th></tr></thead>
                        <tbody>${blockedRows}</tbody>
                    </table>
                </div>
            </div>` : '<div class="waf-no-blocks">Aucune adresse IP bloquée actuellement</div>'}`;

        document.getElementById('attacksBlocked').textContent = blocked.count;
    } catch {
        document.getElementById('wafSection').innerHTML =
            '<p style="color:var(--danger);padding:1rem">Erreur de chargement du statut WAF</p>';
    }
}

async function testWAF() {
    const resultDiv = document.getElementById('wafTestResult');
    resultDiv.className = 'test-result test-result--warning';

    const limit = wafRateLimit || 50;
    const total = limit + 5;
    let sent = 0, blocked = false;

    for (let i = 0; i < total; i++) {
        resultDiv.textContent = `Test en cours — ${i + 1} / ${total} requêtes envoyées...`;
        try {
            const res = await fetch(`${API_BASE_URL}/health`);
            sent++;
            if (res.status === 429) {
                blocked = true;
                resultDiv.className = 'test-result test-result--danger';
                resultDiv.textContent = `WAF déclenché à la requête ${sent} / ${limit} — adresse IP bloquée (HTTP 429). Utilisez « Débloquer les IPs » pour rétablir l'accès.`;
                break;
            }
        } catch {
            sent++;
            const wafCheck = await fetch(`${API_BASE_URL}/security/waf/status`)
                .then(r => r.json()).catch(() => null);
            if (wafCheck?.is_blocked) {
                blocked = true;
                resultDiv.className = 'test-result test-result--danger';
                resultDiv.textContent = `WAF déclenché à la requête ${sent} — adresse IP bloquée. Utilisez « Débloquer les IPs » pour rétablir l'accès.`;
            }
            break;
        }
    }
    if (!blocked) {
        resultDiv.className = 'test-result test-result--warning';
        resultDiv.textContent = `${sent} requêtes envoyées — limite de ${limit} non atteinte. Vérifiez que le compteur WAF est réinitialisé avant le test.`;
    }
    loadWAFStatus();
}

async function unblockAll() {
    try {
        const res  = await authFetch('/security/waf/unblock', adminToken, { method: 'POST' });
        const data = await res.json();
        const resultDiv = document.getElementById('wafTestResult');
        resultDiv.className = 'test-result test-result--success';
        resultDiv.textContent = data.message;
        loadWAFStatus();
    } catch {
        alert('Erreur lors du débloquage des adresses IP.');
    }
}

function startWAFAutoRefresh() {
    loadWAFStatus();
    wafRefreshInterval = setInterval(() => {
        loadWAFStatus();
        loadOverviewStats();
    }, 5000);
}

// =============================================
// INIT
// =============================================

window.addEventListener('load', () => {
    // requireAuth() vérifie seulement qu'un token existe
    adminToken = requireAuth();
    if (!adminToken) return;

    const { name, role } = getStoredAuth();
    currentRole = role;

    // Seuls admin et agent ont accès ; les guests sont renvoyés à l'analyse
    if (currentRole !== 'admin' && currentRole !== 'agent') {
        window.location.href = 'index.html';
        return;
    }

    const userNameEl = document.getElementById('userName');
    if (name && userNameEl) userNameEl.textContent = name;

    document.getElementById('logoutBtn').addEventListener('click', logout);

    if (currentRole === 'agent') {
        // Masquer tous les éléments réservés aux admins
        document.querySelectorAll('.admin-only-el').forEach(el => el.style.display = 'none');
        // Sous-titre adapté
        const sub = document.querySelector('.page-header p');
        if (sub) sub.textContent = 'Supervision des journaux d\'audit, des détections et des métriques système';
        // Charger les données accessibles aux agents
        loadOverviewStats();
        loadWAFStatus();
    } else {
        // Admin : comportement normal complet
        loadUsers();
        loadOverviewStats();
        startWAFAutoRefresh();
        fetch(`${API_BASE_URL}/security/waf/status`)
            .then(r => r.json())
            .then(d => { wafRateLimit = d.max_requests || 50; })
            .catch(() => {});
    }
});
