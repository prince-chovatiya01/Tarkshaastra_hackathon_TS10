// Leaflet map — Ahmedabad, dark tiles, zone polygons, pipe segments (real data), anomaly markers
var map = null;
var anomalyMarkers = {};
var zoneLayer = null;
var pipeLayer = null;
var zonesVisible = true;
var pipesVisible = true;

var zoneColors = {
    'Zone A': '#00f3ff',
    'Zone B': '#a855f7',
    'Zone C': '#ffaa00'
};
var typeColors = {
    'pipe_burst': '#ff3333',
    'slow_seepage': '#22d3ee',
    'illegal_tap': '#ffaa00'
};
var typeIcons = {
    'pipe_burst': '💥',
    'slow_seepage': '💧',
    'illegal_tap': '🔌'
};

function initMap() {
    var mapEl = document.getElementById('leaflet-map');
    if (!mapEl || map) return;

    map = L.map('leaflet-map', {
        center: [23.0, 72.50],
        zoom: 11,
        zoomControl: true
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: 'CartoDB Dark Matter',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    loadPipeSegments();

    // Wire up toggle buttons
    var togglePipes = document.getElementById('togglePipesBtn');
    if (togglePipes) togglePipes.addEventListener('click', function () { toggleLayer('pipes'); });

    // Dynamic pipe dot sizing on zoom
    map.on('zoomend', function () { resizePipeDots(); });

    setTimeout(function () { map.invalidateSize(); }, 200);
}

function toggleLayer(which) {
    if (which === 'pipes' && pipeLayer) {
        pipesVisible = !pipesVisible;
        if (pipesVisible) { map.addLayer(pipeLayer); } else { map.removeLayer(pipeLayer); }
        var btn = document.getElementById('togglePipesBtn');
        if (btn) btn.style.borderColor = pipesVisible ? '#00f3ff' : 'rgba(255,255,255,0.12)';
    }
}

function getPipeRadius() {
    if (!map) return 1;
    var z = map.getZoom();
    // zoom 9 → 0.3, zoom 11 → 1, zoom 13 → 2, zoom 15 → 3, zoom 17+ → 4
    if (z <= 9) return 0.1;
    if (z <= 10) return 0.3;
    if (z <= 11) return 0.7;
    if (z <= 12) return 1;
    if (z <= 13) return 1.5;
    if (z <= 14) return 2;
    if (z <= 15) return 3;
    return 4;
}

function getPipeOpacity() {
    if (!map) return 0.4;
    var z = map.getZoom();
    if (z <= 9) return 0.15;
    if (z <= 10) return 0.25;
    if (z <= 11) return 0.3;
    return 0.5;
}

function resizePipeDots() {
    if (!pipeLayer) return;
    var r = getPipeRadius();
    var op = getPipeOpacity();
    pipeLayer.eachLayer(function (layer) {
        if (layer.setRadius) {
            layer.setRadius(r);
            layer.setStyle({ fillOpacity: op, opacity: op });
        }
    });
}

function loadPipeSegments() {
    fetch('/data/pipe_segments.geojson')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var initRadius = getPipeRadius();
            var initOpacity = getPipeOpacity();
            pipeLayer = L.geoJSON(data, {
                pointToLayer: function (feature, latlng) {
                    var zone = feature.properties.zone;
                    var color = zoneColors[zone] || '#555555';
                    return L.circleMarker(latlng, {
                        radius: initRadius,
                        fillColor: color,
                        color: color,
                        weight: 0,
                        opacity: initOpacity,
                        fillOpacity: initOpacity,
                        interactive: false
                    });
                }
            }).addTo(map);
        });
}

function addAnomalyMarker(data) {
    if (!map) return;
    if (anomalyMarkers[data.id]) return;

    var color = typeColors[data.anomaly_type] || '#ffffff';
    var icon = typeIcons[data.anomaly_type] || '⚠';

    // Create a styled div icon instead of a pulsing circle
    var divIcon = L.divIcon({
        className: 'anomaly-marker-icon',
        html: '<div class="anomaly-pin" style="' +
            'background:' + color + ';' +
            'box-shadow: 0 0 8px ' + color + ', 0 0 16px ' + color + '40;' +
            '">' + icon + '</div>',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
        popupAnchor: [0, -14]
    });

    var marker = L.marker([data.lat, data.lng], { icon: divIcon }).addTo(map);

    var role = getRole();
    var dispatchBtn = '';
    if (role === 'zone_engineer' && data.status === 'ACTIVE') {
        dispatchBtn = '<br><button class="btn-primary" style="margin-top:8px;padding:5px 12px;font-size:12px;" onclick="openDispatchModal(' + data.id + ',\'' + data.segment_id + '\',\'' + data.zone + '\',\'' + data.anomaly_type + '\',\'' + data.urgency + '\',' + data.est_loss_litres + ')">Dispatch Crew</button>';
    }

    marker.bindPopup(
        '<div style="font-family:Rajdhani,sans-serif;color:#fff;min-width:200px;">' +
        '<strong style="font-family:Orbitron,sans-serif;font-size:13px;">' + data.segment_id + '</strong><br>' +
        '<span style="color:' + color + ';font-weight:700;text-transform:uppercase;">' + data.anomaly_type.replace('_', ' ') + '</span><br>' +
        'Zone: ' + data.zone + '<br>' +
        'Urgency: ' + data.urgency + '<br>' +
        'Loss: ' + (data.est_loss_litres || 0).toFixed(0) + ' L/day<br>' +
        'Confidence: ' + ((data.confidence || 0) * 100).toFixed(1) + '%' +
        dispatchBtn +
        '</div>',
        { className: 'dark-popup' }
    );

    marker._anomalyData = data;
    anomalyMarkers[data.id] = marker;
}

function updateMarkerStatus(anomalyId, status) {
    var marker = anomalyMarkers[anomalyId];
    if (!marker) return;
    if (status === 'RESOLVED' || status === 'FALSE_ALARM') {
        var el = marker.getElement();
        if (el) {
            var pin = el.querySelector('.anomaly-pin');
            if (pin) {
                pin.style.background = '#22c55e';
                pin.style.boxShadow = '0 0 8px #22c55e, 0 0 16px #22c55e40';
                pin.textContent = '✓';
            }
        }
    } else if (status === 'DISPATCHED') {
        var el = marker.getElement();
        if (el) {
            var pin = el.querySelector('.anomaly-pin');
            if (pin) {
                pin.style.background = '#ffaa00';
                pin.style.boxShadow = '0 0 8px #ffaa00, 0 0 16px #ffaa0040';
            }
        }
    }
}

function getZone() {
    var select = document.getElementById('zoneFilterSelect');
    return select ? select.value : '';
}
