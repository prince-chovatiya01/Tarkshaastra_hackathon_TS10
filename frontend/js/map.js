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

    loadZones();
    loadPipeSegments();

    // Wire up toggle buttons
    var toggleZones = document.getElementById('toggleZonesBtn');
    var togglePipes = document.getElementById('togglePipesBtn');
    if (toggleZones) toggleZones.addEventListener('click', function() { toggleLayer('zones'); });
    if (togglePipes) togglePipes.addEventListener('click', function() { toggleLayer('pipes'); });

    setTimeout(function() { map.invalidateSize(); }, 200);
}

function toggleLayer(which) {
    if (which === 'zones' && zoneLayer) {
        zonesVisible = !zonesVisible;
        if (zonesVisible) { map.addLayer(zoneLayer); } else { map.removeLayer(zoneLayer); }
        var btn = document.getElementById('toggleZonesBtn');
        if (btn) btn.style.borderColor = zonesVisible ? '#00f3ff' : 'rgba(255,255,255,0.12)';
    }
    if (which === 'pipes' && pipeLayer) {
        pipesVisible = !pipesVisible;
        if (pipesVisible) { map.addLayer(pipeLayer); } else { map.removeLayer(pipeLayer); }
        var btn = document.getElementById('togglePipesBtn');
        if (btn) btn.style.borderColor = pipesVisible ? '#00f3ff' : 'rgba(255,255,255,0.12)';
    }
}

function loadZones() {
    fetch('/data/zones.geojson')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            zoneLayer = L.geoJSON(data, {
                style: function(feature) {
                    var zone = feature.properties.zone_name;
                    var color = zoneColors[zone] || '#ffffff';
                    return {
                        color: color,
                        weight: 2,
                        opacity: 0.6,
                        fillColor: color,
                        fillOpacity: 0.05,
                        dashArray: '6 4'
                    };
                },
                onEachFeature: function(feature, layer) {
                    layer.bindTooltip(feature.properties.zone_name, {
                        permanent: false,
                        className: 'zone-tooltip'
                    });
                }
            }).addTo(map);
        });
}

function loadPipeSegments() {
    fetch('/data/pipe_segments.geojson')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            pipeLayer = L.geoJSON(data, {
                pointToLayer: function(feature, latlng) {
                    var zone = feature.properties.zone;
                    var color = zoneColors[zone] || '#555555';
                    return L.circleMarker(latlng, {
                        radius: 2,
                        fillColor: color,
                        color: color,
                        weight: 0,
                        opacity: 0.4,
                        fillOpacity: 0.3
                    });
                },
                onEachFeature: function(feature, layer) {
                    layer.bindTooltip(
                        '<b>' + feature.properties.segment_id + '</b><br>' + feature.properties.zone,
                        { permanent: false, className: 'zone-tooltip' }
                    );
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
