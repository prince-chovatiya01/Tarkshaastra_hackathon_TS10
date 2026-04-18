// Leaflet map — Ahmedabad centered, dark tiles, zone polygons, pipe segments, anomaly markers
var map = null;
var anomalyMarkers = {};
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

function initMap() {
    var mapEl = document.getElementById('leaflet-map');
    if (!mapEl || map) return;

    map = L.map('leaflet-map', {
        center: [23.0225, 72.5714],
        zoom: 12,
        zoomControl: true
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: 'CartoDB Dark Matter',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    loadZones();
    loadPipeSegments();

    setTimeout(function() { map.invalidateSize(); }, 200);
}

function loadZones() {
    fetch('/data/zones.geojson')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            L.geoJSON(data, {
                style: function(feature) {
                    var zone = feature.properties.zone_name;
                    var color = zoneColors[zone] || '#ffffff';
                    return {
                        color: color,
                        weight: 2,
                        opacity: 0.8,
                        fillColor: color,
                        fillOpacity: 0.08
                    };
                },
                onEachFeature: function(feature, layer) {
                    layer.bindTooltip(feature.properties.zone_name + ' (' + feature.properties.ward_name + ')', {
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
            L.geoJSON(data, {
                style: function() {
                    return {
                        color: '#555555',
                        weight: 2,
                        opacity: 0.5
                    };
                },
                onEachFeature: function(feature, layer) {
                    layer.bindTooltip(feature.properties.segment_id, { permanent: false });
                }
            }).addTo(map);
        });
}

function addAnomalyMarker(data) {
    if (!map) return;
    if (anomalyMarkers[data.id]) return;

    var color = typeColors[data.anomaly_type] || '#ffffff';
    var marker = L.circleMarker([data.lat, data.lng], {
        radius: 10,
        fillColor: color,
        color: color,
        weight: 2,
        opacity: 0.9,
        fillOpacity: 0.5,
        className: 'anomaly-pulse'
    }).addTo(map);

    var role = getRole();
    var dispatchBtn = '';
    if (role === 'zone_engineer') {
        dispatchBtn = '<br><button class="btn-primary" style="margin-top:8px;padding:5px 12px;font-size:12px;" onclick="openDispatchModal(' + data.id + ',\'' + data.segment_id + '\',\'' + data.zone + '\',\'' + data.anomaly_type + '\',\'' + data.urgency + '\',' + data.est_loss_litres + ')">Dispatch Crew</button>';
    }

    marker.bindPopup(
        '<div style="font-family:Rajdhani,sans-serif;color:#fff;min-width:180px;">' +
        '<strong style="font-family:Orbitron,sans-serif;font-size:13px;">' + data.segment_id + '</strong><br>' +
        '<span style="color:' + color + ';font-weight:700;text-transform:uppercase;">' + data.anomaly_type.replace('_', ' ') + '</span><br>' +
        'Zone: ' + data.zone + '<br>' +
        'Urgency: ' + data.urgency + '<br>' +
        'Loss: ' + data.est_loss_litres + ' L/day<br>' +
        'Confidence: ' + (data.confidence * 100).toFixed(1) + '%' +
        dispatchBtn +
        '</div>',
        { className: 'dark-popup' }
    );

    anomalyMarkers[data.id] = marker;
}

function updateMarkerStatus(anomalyId, status) {
    var marker = anomalyMarkers[anomalyId];
    if (!marker) return;
    if (status === 'RESOLVED' || status === 'FALSE_ALARM') {
        marker.setStyle({ fillColor: '#22c55e', color: '#22c55e', fillOpacity: 0.3, opacity: 0.5 });
    } else if (status === 'DISPATCHED') {
        marker.setStyle({ fillColor: '#ffaa00', color: '#ffaa00' });
    } else if (status === 'ACTIVE') {
        var origColor = marker.options._origColor || '#ff3333';
        marker.setStyle({ fillColor: origColor, color: origColor, fillOpacity: 0.5, opacity: 0.9 });
    }
}
