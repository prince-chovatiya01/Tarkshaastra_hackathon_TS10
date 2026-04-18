// Anomaly list — renders cards in sidebar, handles prepend and status updates
var typeBadgeClass = {
    'pipe_burst': 'badge-burst',
    'slow_seepage': 'badge-seepage',
    'illegal_tap': 'badge-tap'
};
var typeLabel = {
    'pipe_burst': 'PIPE BURST',
    'slow_seepage': 'SEEPAGE',
    'illegal_tap': 'ILLEGAL TAP'
};

function prependAnomalyCard(data, skipAnimation) {
    var list = document.getElementById('anomaly-list');
    if (!list) return;

    var card = document.createElement('div');
    card.className = 'anomaly-card-item';
    card.id = 'anomaly-card-' + data.id;
    card.setAttribute('data-anomaly-id', data.id);

    var borderColor = '#ff3333';
    if (data.anomaly_type === 'slow_seepage') borderColor = '#22d3ee';
    if (data.anomaly_type === 'illegal_tap') borderColor = '#ffaa00';

    var statusColor = '#00f3ff';
    if (data.status === 'DISPATCHED') statusColor = '#ffaa00';
    if (data.status === 'RESOLVED') statusColor = '#22c55e';

    var role = getRole();
    var dispatchHtml = '';
    if (role === 'zone_engineer' && data.status === 'ACTIVE') {
        dispatchHtml = '<button class="btn-dispatch" id="dispatch-btn-' + data.id + '" onclick="openDispatchModal(' +
            data.id + ',\'' + data.segment_id + '\',\'' + data.zone + '\',\'' + data.anomaly_type + '\',\'' +
            data.urgency + '\',' + data.est_loss_litres + ')">DISPATCH</button>';
    }

    card.innerHTML =
        '<div class="anomaly-card-border" style="background:' + borderColor + ';"></div>' +
        '<div class="anomaly-card-body">' +
        '<div class="anomaly-card-header">' +
        '<span class="mono" style="font-size:13px;color:var(--text-primary);">' + data.segment_id + '</span>' +
        '<span class="badge ' + (typeBadgeClass[data.anomaly_type] || '') + '">' + (typeLabel[data.anomaly_type] || data.anomaly_type) + '</span>' +
        '</div>' +
        '<div class="anomaly-card-details">' +
        '<span>' + data.zone + '</span>' +
        '<span>Urgency: <strong>' + data.urgency + '</strong></span>' +
        '<span>Loss: <strong class="mono">' + (data.est_loss_litres || 0).toFixed(0) + ' L</strong></span>' +
        '</div>' +
        '<div class="anomaly-card-footer">' +
        '<span class="anomaly-status" id="anomaly-status-' + data.id + '" style="color:' + statusColor + ';">' + data.status + '</span>' +
        dispatchHtml +
        '</div>' +
        '</div>';

    if (!skipAnimation) {
        card.style.animation = 'slideIn 0.3s ease, highlightNew 2s ease';
    }
    list.prepend(card);
}

function updateAnomalyCardStatus(anomalyId, newStatus) {
    var statusEl = document.getElementById('anomaly-status-' + anomalyId);
    if (statusEl) {
        statusEl.textContent = newStatus;
        var color = '#00f3ff';
        if (newStatus === 'DISPATCHED') color = '#ffaa00';
        if (newStatus === 'RESOLVED') color = '#22c55e';
        if (newStatus === 'FALSE_ALARM') color = '#22c55e';
        if (newStatus === 'UNRESOLVED') color = '#ff3333';
        statusEl.style.color = color;
    }
    var dispatchBtn = document.getElementById('dispatch-btn-' + anomalyId);
    if (dispatchBtn && newStatus !== 'ACTIVE') {
        dispatchBtn.style.display = 'none';
    }
}
