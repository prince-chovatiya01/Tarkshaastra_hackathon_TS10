// Auth utilities — login API call, JWT management, role extraction
function getToken() {
    return localStorage.getItem('gwd_token');
}

function setToken(token) {
    localStorage.setItem('gwd_token', token);
}

function clearAuth() {
    localStorage.removeItem('gwd_token');
    localStorage.removeItem('gwd_role');
    localStorage.removeItem('gwd_user');
    localStorage.removeItem('gwd_zone');
}

function decodeJwt(token) {
    var parts = token.split('.');
    if (parts.length !== 3) return null;
    var payload = parts[1];
    var decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decoded);
}

function getRole() {
    return localStorage.getItem('gwd_role') || '';
}

function getZone() {
    return localStorage.getItem('gwd_zone') || '';
}

function getUserName() {
    return localStorage.getItem('gwd_user') || '';
}

function authHeader() {
    var token = getToken();
    if (!token) return {};
    return { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' };
}

function isTokenExpired() {
    var token = getToken();
    if (!token) return true;
    var payload = decodeJwt(token);
    if (!payload || !payload.exp) return true;
    return Date.now() / 1000 > payload.exp;
}

function checkAuth() {
    if (!getToken() || isTokenExpired()) {
        clearAuth();
        window.location.href = '/';
        return false;
    }
    return true;
}

function logout() {
    clearAuth();
    window.location.href = '/';
}

function initLoginForm() {
    var form = document.getElementById('loginForm');
    var errorEl = document.getElementById('loginError');
    if (!form) return;
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        var username = document.getElementById('loginUsername').value.trim();
        var password = document.getElementById('loginPassword').value;
        if (errorEl) errorEl.textContent = '';

        fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username, password: password })
        })
        .then(function(res) {
            if (!res.ok) throw new Error('Invalid credentials');
            return res.json();
        })
        .then(function(data) {
            setToken(data.token);
            localStorage.setItem('gwd_role', data.role);
            localStorage.setItem('gwd_user', data.full_name);
            localStorage.setItem('gwd_zone', data.assigned_zone || '');
            window.location.href = '/dashboard';
        })
        .catch(function(err) {
            if (errorEl) errorEl.textContent = 'Login failed. Check your credentials.';
        });
    });
}
