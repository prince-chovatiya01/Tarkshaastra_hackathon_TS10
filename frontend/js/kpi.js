// KPI cards — fetch and render animated counters
var currentKpis = { total_active_anomalies: 0, total_daily_loss_litres: 0, zone_nrw: {} };

function refreshKpis() {
    fetch('/api/dashboard/kpis', { headers: authHeader() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            animateCounter('kpi-active-count', currentKpis.total_active_anomalies, data.total_active_anomalies);
            animateCounter('kpi-loss-count', currentKpis.total_daily_loss_litres, data.total_daily_loss_litres, true);
            currentKpis = data;
            renderNrwBars(data.zone_nrw);
        })
        .catch(function(err) {
            console.error('KPI fetch failed:', err);
        });
}

function animateCounter(elementId, fromVal, toVal, isFloat) {
    var el = document.getElementById(elementId);
    if (!el) return;
    var duration = 600;
    var startTime = null;
    var from = fromVal || 0;
    var to = toVal || 0;

    function step(timestamp) {
        if (!startTime) startTime = timestamp;
        var progress = Math.min((timestamp - startTime) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        var current = from + (to - from) * eased;
        el.textContent = isFloat ? current.toFixed(0) : Math.round(current);
        if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

function renderNrwBars(zoneNrw) {
    var container = document.getElementById('nrw-bars');
    if (!container) return;
    container.innerHTML = '';
    var zones = ['Zone A', 'Zone B', 'Zone C'];
    var colors = { 'Zone A': '#00f3ff', 'Zone B': '#a855f7', 'Zone C': '#ffaa00' };
    zones.forEach(function(z) {
        var val = zoneNrw[z] || 0;
        var bar = document.createElement('div');
        bar.style.cssText = 'margin-bottom:8px;';
        bar.innerHTML =
            '<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">' +
            '<span style="color:' + colors[z] + ';">' + z + '</span>' +
            '<span class="mono" style="color:var(--text-secondary);">' + val.toFixed(1) + '%</span></div>' +
            '<div style="height:6px;background:rgba(255,255,255,0.08);border-radius:3px;overflow:hidden;">' +
            '<div style="height:100%;width:' + Math.min(val, 100) + '%;background:' + colors[z] + ';border-radius:3px;transition:width 0.5s ease;"></div></div>';
        container.appendChild(bar);
    });
}
