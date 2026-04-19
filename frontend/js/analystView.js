// Analyst view — data table, filters, CSV export, false positive flagging, Chart.js
function initAnalystView() {
    attachFilterListeners();
    loadAnomalyHistory();
    loadFpRate();
}

function attachFilterListeners() {
    var applyBtn = document.getElementById('applyFiltersBtn');
    if (applyBtn) applyBtn.addEventListener('click', loadAnomalyHistory);
    var exportBtn = document.getElementById('exportCsvBtn');
    if (exportBtn) exportBtn.addEventListener('click', exportCsv);
}

function buildFilterParams() {
    var params = [];
    var zone = document.getElementById('filterZone');
    var dateFrom = document.getElementById('filterDateFrom');
    var dateTo = document.getElementById('filterDateTo');
    var type = document.getElementById('filterType');
    if (zone && zone.value) params.push('zone=' + encodeURIComponent(zone.value));
    if (dateFrom && dateFrom.value) params.push('date_from=' + encodeURIComponent(dateFrom.value + 'T00:00:00'));
    if (dateTo && dateTo.value) params.push('date_to=' + encodeURIComponent(dateTo.value + 'T23:59:59'));
    if (type && type.value) params.push('anomaly_type=' + encodeURIComponent(type.value));
    return params.length > 0 ? '?' + params.join('&') : '';
}

function loadAnomalyHistory() {
    var qs = buildFilterParams();
    fetch('/api/anomalies' + qs, { headers: authHeader() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            renderTable(data);
            renderChart(data);
        });
}

function renderTable(anomalies) {
    var tbody = document.getElementById('analystTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    anomalies.forEach(function(a) {
        var tr = document.createElement('tr');
        var fpCell = '—';
        if (a.is_false_positive) {
            fpCell = '<span style="color:#22c55e;font-weight:700;">✓ Crew confirmed</span>';
        } else if (a.status === 'FALSE_ALARM') {
            fpCell = '<span style="color:#22c55e;font-weight:700;">✓ Crew confirmed</span>';
        }
        tr.innerHTML =
            '<td>' + (a.detected_at ? a.detected_at.slice(0, 19).replace('T', ' ') : '--') + '</td>' +
            '<td class="mono">' + a.segment_id + '</td>' +
            '<td>' + a.zone + '</td>' +
            '<td>' + a.anomaly_type.replace('_', ' ') + '</td>' +
            '<td>' + a.urgency + '</td>' +
            '<td class="mono">' + (a.est_loss_litres || 0).toFixed(0) + '</td>' +
            '<td class="mono">' + ((a.confidence || 0) * 100).toFixed(1) + '%</td>' +
            '<td>' + a.status + '</td>' +
            '<td>' + fpCell + '</td>';
        tbody.appendChild(tr);
    });
}

function loadFpRate() {
    fetch('/api/stats/false-positive-rate', { headers: authHeader() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var el = document.getElementById('fpRateValue');
            if (el) el.textContent = data.rate_percent.toFixed(1) + '% (' + data.false_positives + '/' + data.total + ')';
        });
}

function exportCsv() {
    var qs = buildFilterParams();
    fetch('/api/anomalies/export' + qs, { headers: authHeader() })
        .then(function(r) { return r.blob(); })
        .then(function(blob) {
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'anomalies_export.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
}

var analystChart = null;
function renderChart(anomalies) {
    var canvas = document.getElementById('anomalyPieChart');
    if (!canvas || typeof Chart === 'undefined') return;
    var counts = { pipe_burst: 0, slow_seepage: 0, illegal_tap: 0 };
    anomalies.forEach(function(a) { if (counts[a.anomaly_type] !== undefined) counts[a.anomaly_type]++; });
    if (analystChart) analystChart.destroy();
    analystChart = new Chart(canvas, {
        type: 'pie',
        data: {
            labels: ['Pipe Burst', 'Slow Seepage', 'Illegal Tap'],
            datasets: [{ data: [counts.pipe_burst, counts.slow_seepage, counts.illegal_tap], backgroundColor: ['#ff3333', '#22d3ee', '#ffaa00'], borderColor: '#14141e', borderWidth: 2 }]
        },
        options: { responsive: true, plugins: { legend: { labels: { color: '#fff', font: { family: 'Rajdhani' } } } } }
    });
}
