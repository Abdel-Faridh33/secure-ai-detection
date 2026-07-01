function getStoredAuth() {
    return {
        token: localStorage.getItem('access_token'),
        role:  localStorage.getItem('user_role'),
        name:  localStorage.getItem('user_name'),
    };
}

function clearAuth() {
    ['access_token', 'user_role', 'user_name', 'user_permissions'].forEach(k =>
        localStorage.removeItem(k)
    );
}

function logout() {
    clearAuth();
    window.location.href = 'login.html';
}

function requireAuth(requiredRole = null) {
    const { token, role } = getStoredAuth();
    if (!token) {
        window.location.href = 'login.html';
        return null;
    }
    if (requiredRole && role !== requiredRole) {
        window.location.href = 'login.html';
        return null;
    }
    return token;
}
