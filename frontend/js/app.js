// Main orchestrator — loads role-appropriate components, manages WebSocket
var ws = null;
var wsRetryCount = 0;
var wsMaxRetry = 10;

function loadComponent(containerId, componentPath) {
    return fetch('/stitch-components/' + componentPath)
        .then(function(r) { return r.text(); })
        .then(function(html) {
            var el = document.getElementById(containerId);
            if (el) el.innerHTML = html;
        });
}

function showToast(message, type) {
    var container = document.getElementById('toast-container');
    if (!container) return;
    var toast = document.createElement('div');
    toast.className = 'toast toast-' + (type || 'success');
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 4000);
}

function initWebSocket() {
    var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    var wsUrl = protocol + '//' + window.location.host + '/ws';
    ws = new WebSocket(wsUrl);

    ws.onopen = function() {
        wsRetryCount = 0;
        var indicator = document.getElementById('wsIndicator');
        if (indicator) {
            indicator.classList.remove('ws-disconnected');
            indicator.classList.add('ws-connected');
        }
    };

    ws.onclose = function() {
        var indicator = document.getElementById('wsIndicator');
        if (indicator) {
            indicator.classList.remove('ws-connected');
            indicator.classList.add('ws-disconnected');
        }
        if (wsRetryCount < wsMaxRetry) {
            var delay = Math.min(1000 * Math.pow(2, wsRetryCount), 30000);
            wsRetryCount++;
            setTimeout(initWebSocket, delay);
        }
    };

    ws.onerror = function() {
        ws.close();
    };

    ws.onmessage = function(event) {
        var msg = JSON.parse(event.data);
        handleWsMessage(msg);
    };
}

function handleWsMessage(msg) {
    var role = getRole();
    if (msg.event === 'new_anomaly') {
        if (typeof refreshKpis === 'function') refreshKpis();
        if (typeof prependAnomalyCard === 'function') {
            var zone = getZone();
            if (role === 'zone_engineer' && zone && msg.data.zone !== zone) return;
            prependAnomalyCard(msg.data);
        }
        if (typeof addAnomalyMarker === 'function' && role !== 'data_analyst') {
            addAnomalyMarker(msg.data);
        }
    } else if (msg.event === 'dispatch_update' || msg.event === 'status_update') {
        if (typeof updateAnomalyCardStatus === 'function') {
            updateAnomalyCardStatus(msg.data.anomaly_id, msg.data.status);
        }
        if (typeof updateMarkerStatus === 'function') {
            updateMarkerStatus(msg.data.anomaly_id, msg.data.status);
        }
        if (typeof refreshKpis === 'function') refreshKpis();
    } else if (msg.event === 'timeout') {
        if (typeof updateAnomalyCardStatus === 'function') {
            updateAnomalyCardStatus(msg.data.anomaly_id, 'ACTIVE');
        }
        showToast('TIMEOUT: Dispatch #' + msg.data.dispatch_id + ' expired. Re-dispatch needed.', 'error');
        if (typeof refreshKpis === 'function') refreshKpis();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    if (!checkAuth()) return;

    var role = getRole();
    var userName = getUserName();
    var roleBadge = document.getElementById('roleBadge');
    var userNameEl = document.getElementById('userName');
    var logoutBtn = document.getElementById('logoutBtn');

    if (roleBadge) roleBadge.textContent = role.replace('_', ' ').toUpperCase();
    if (userNameEl) userNameEl.textContent = userName;
    if (logoutBtn) logoutBtn.addEventListener('click', logout);

    loadComponent('sidebar-container', 'sidebar-panel.html').then(function() {
        loadComponent('kpi-slot', 'kpi-cards.html').then(function() {
            if (typeof refreshKpis === 'function') refreshKpis();
        });
        loadAnomalyFeed();
    });

    if (role === 'data_analyst') {
        loadComponent('main-content', 'analyst-table.html').then(function() {
            if (typeof initAnalystView === 'function') initAnalystView();
        });
    } else {
        loadComponent('main-content', 'map-container.html').then(function() {
            if (typeof initMap === 'function') initMap();
        });
    }

    loadComponent('dispatch-modal-overlay', 'dispatch-modal.html');
    initWebSocket();
});

function loadAnomalyFeed() {
    fetch('/api/dashboard/anomalies', { headers: authHeader() })
        .then(function(r) { return r.json(); })
        .then(function(anomalies) {
            var list = document.getElementById('anomaly-list');
            if (!list) return;
            list.innerHTML = '';
            anomalies.forEach(function(a) {
                if (typeof prependAnomalyCard === 'function') prependAnomalyCard(a, true);
            });
        })
        .catch(function(err) {
            console.error('Failed to load anomaly feed:', err);
        });
}
