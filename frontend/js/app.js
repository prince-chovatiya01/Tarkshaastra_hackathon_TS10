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

    // Show Crew Keys button for zone engineers
    if (role === 'zone_engineer') {
        var crewBtn = document.getElementById('crewKeysBtn');
        if (crewBtn) crewBtn.style.display = 'inline-block';
    }

    loadComponent('sidebar-container', 'sidebar-panel.html').then(function() {
        loadComponent('kpi-slot', 'kpi-cards.html').then(function() {
            if (typeof refreshKpis === 'function') refreshKpis();
        });
        loadAnomalyFeed();
        // Wire up zone filter after sidebar loads
        setTimeout(function() {
            var zoneSelect = document.getElementById('zoneFilterSelect');
            if (zoneSelect) {
                zoneSelect.addEventListener('change', function() {
                    filterAnomalies(this.value);
                });
            }
        }, 300);
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
    loadComponent('crew-manager-overlay', 'crew-manager.html');
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
                if (typeof addAnomalyMarker === 'function') addAnomalyMarker(a);
            });
        })
        .catch(function(err) {
            console.error('Failed to load anomaly feed:', err);
        });
}

function filterAnomalies(zone) {
    // Filter anomaly cards in sidebar
    var cards = document.querySelectorAll('.anomaly-card-item');
    cards.forEach(function(card) {
        var cardZone = card.querySelector('.anomaly-card-details span');
        if (!zone || (cardZone && cardZone.textContent === zone)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
    // Filter map markers
    if (typeof anomalyMarkers !== 'undefined') {
        Object.keys(anomalyMarkers).forEach(function(id) {
            var marker = anomalyMarkers[id];
            if (!marker || !marker._anomalyData) return;
            if (!zone || marker._anomalyData.zone === zone) {
                if (map && !map.hasLayer(marker)) map.addLayer(marker);
            } else {
                if (map && map.hasLayer(marker)) map.removeLayer(marker);
            }
        });
    }
}
