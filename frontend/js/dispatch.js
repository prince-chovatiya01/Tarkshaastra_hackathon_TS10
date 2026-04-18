// Dispatch module — crew selector modal, dispatch API
var currentDispatchAnomalyId = null;

function openDispatchModal(anomalyId, segmentId, zone, anomalyType, urgency, estLoss) {
    currentDispatchAnomalyId = anomalyId;
    var overlay = document.getElementById('dispatch-modal-overlay');
    if (overlay) overlay.classList.add('active');
    var summaryEl = document.getElementById('dispatch-anomaly-summary');
    if (summaryEl) {
        summaryEl.innerHTML = '<div><strong>Segment:</strong> ' + segmentId + '</div><div><strong>Type:</strong> ' + anomalyType.replace('_',' ').toUpperCase() + '</div><div><strong>Zone:</strong> ' + zone + '</div><div><strong>Urgency:</strong> ' + urgency + '</div><div><strong>Est. Loss:</strong> ' + estLoss + ' L/day</div>';
    }
    var dropdown = document.getElementById('crewSelect');
    var noCrew = document.getElementById('noCrewMsg');
    if (dropdown) dropdown.innerHTML = '<option value="">Loading...</option>';
    if (noCrew) noCrew.style.display = 'none';
    fetch('/api/crew?zone=' + encodeURIComponent(zone) + '&available=true', { headers: authHeader() })
        .then(function(r) { return r.json(); })
        .then(function(crew) {
            if (!dropdown) return;
            dropdown.innerHTML = '';
            if (crew.length === 0) {
                dropdown.innerHTML = '<option value="">No crew available</option>';
                if (noCrew) noCrew.style.display = 'block';
                return;
            }
            crew.forEach(function(c) {
                var opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.name + ' (' + c.phone + ')';
                dropdown.appendChild(opt);
            });
        });
}

function closeDispatchModal() {
    var overlay = document.getElementById('dispatch-modal-overlay');
    if (overlay) overlay.classList.remove('active');
    currentDispatchAnomalyId = null;
}

function confirmDispatch() {
    var dropdown = document.getElementById('crewSelect');
    if (!dropdown || !dropdown.value) return;
    var crewId = parseInt(dropdown.value, 10);
    var sendBtn = document.getElementById('sendDispatchBtn');
    if (sendBtn) { sendBtn.disabled = true; sendBtn.textContent = 'SENDING...'; }
    fetch('/api/dispatch', {
        method: 'POST',
        headers: authHeader(),
        body: JSON.stringify({ anomaly_id: currentDispatchAnomalyId, crew_member_id: crewId })
    })
    .then(function(r) {
        if (!r.ok) return r.json().then(function(d) { throw new Error(d.detail || 'Dispatch failed'); });
        return r.json();
    })
    .then(function() {
        closeDispatchModal();
        if (typeof showToast === 'function') showToast('Work order dispatched', 'success');
    })
    .catch(function(err) {
        if (typeof showToast === 'function') showToast(err.message, 'error');
    })
    .finally(function() {
        if (sendBtn) { sendBtn.disabled = false; sendBtn.textContent = 'SEND WORK ORDER'; }
    });
}
