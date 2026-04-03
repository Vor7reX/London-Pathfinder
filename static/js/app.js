/**
 * Main application logic for London Pathfinder.
 * Handles map rendering, API communication, and UI state.
 */

// Initialize Map
const map = L.map('map', { zoomControl: false }).setView([51.5074, -0.1278], 13);
if (window.innerWidth > 768) { L.control.zoom({ position: 'topright' }).addTo(map); }

L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(map);

// Global State
let dynamicLayers = []; 
let explorationLayers = []; 
let stationLookup = {}; 
let allStations = [];
let baseNetworkLayer = L.layerGroup().addTo(map); 
let animTimer = null; 
let pathTimer = null; 

// Mobile Panel Management
function toggleSidebar() {
    if(window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.toggle('collapsed');
    }
}

function collapseSidebar() {
    if(window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.add('collapsed');
    }
}

function expandSidebar() {
    if(window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.remove('collapsed');
    }
}

function createStationTooltip(node) {
    let linesHtml = node.lines.map(l => {
        let imgTag = l.logo ? `<img src="/static/line_logo/${l.logo}">` : '';
        return `<span class="tooltip-line" style="background-color: ${l.color};">${imgTag}${l.name}</span>`;
    }).join('');
    return `<div style="text-align:left;"><strong style="font-size:14px; display:block; margin-bottom:5px;">${node.name}</strong><div>${linesHtml}</div></div>`;
}

// Autocomplete Logic
function setupAutocomplete(inputId, hiddenId, suggestionsId) {
    const input = document.getElementById(inputId);
    const hidden = document.getElementById(hiddenId);
    const suggestions = document.getElementById(suggestionsId);

    input.addEventListener('input', function() {
        const val = this.value.toLowerCase().trim();
        suggestions.innerHTML = ''; 
        
        if (!val) { suggestions.style.display = 'none'; hidden.value = ''; return; }
        const matches = allStations.filter(st => st.name.toLowerCase().includes(val));
        if (matches.length === 0) { suggestions.style.display = 'none'; return; }
        
        matches.forEach(st => {
            const div = document.createElement('div');
            div.className = 'suggestion-item';
            const regex = new RegExp(`(${val})`, "gi");
            div.innerHTML = st.name.replace(regex, "<b>$1</b>");
            
            div.addEventListener('click', () => {
                input.value = st.name; hidden.value = st.id; suggestions.style.display = 'none';
            });
            suggestions.appendChild(div);
        });
        suggestions.style.display = 'block';
    });

    document.addEventListener('click', function(e) {
        if (e.target !== input && e.target !== suggestions) { suggestions.style.display = 'none'; }
    });
    
    input.addEventListener('focus', expandSidebar);
}

// Fetch Initial Data
fetch('/api/stations').then(res => res.json()).then(data => {
    allStations = data;
    setupAutocomplete('start_input', 'start_node', 'start_suggestions');
    setupAutocomplete('target_input', 'target_node', 'target_suggestions');
    
    // Set default stations for demo purposes
    const defStart = allStations.find(s => s.id == "145") || allStations[0]; 
    const defTarget = allStations.find(s => s.id == "273") || allStations[1]; 
    document.getElementById('start_input').value = defStart.name; document.getElementById('start_node').value = defStart.id;
    document.getElementById('target_input').value = defTarget.name; document.getElementById('target_node').value = defTarget.id;
});

fetch('/api/network').then(res => res.json()).then(data => {
    data.edges.forEach(edge => { L.polyline(edge.coords, {color: edge.color, weight: 3, opacity: 0.5}).addTo(baseNetworkLayer); });
    data.nodes.forEach(node => {
        const key = node.coord.join(',');
        stationLookup[key] = node;
        L.circleMarker(node.coord, {radius: 4, color: '#ffffff', weight: 1, fillColor: '#888888', fillOpacity: 1})
         .bindTooltip(createStationTooltip(node), {direction: 'top', offset: [0, -10], className: 'custom-tooltip', sticky: true})
         .addTo(baseNetworkLayer);
    });
});

function clearMap() {
    dynamicLayers.forEach(layer => map.removeLayer(layer));
    dynamicLayers = [];
    explorationLayers.forEach(layer => map.removeLayer(layer));
    explorationLayers = [];
}

// Reset System State
function resetSystem() {
    if (animTimer) clearInterval(animTimer);
    if (pathTimer) clearInterval(pathTimer);
    
    clearMap();
    
    if (!map.hasLayer(baseNetworkLayer)) {
        map.addLayer(baseNetworkLayer);
    }
    
    document.getElementById('itinerary').innerHTML = "Select a route to generate the itinerary.";
    document.getElementById('stats').innerText = "System ready. Awaiting coordinates.";
    document.getElementById('calc_btn').disabled = false;
    document.getElementById('calc_btn').innerText = "INITIATE SCAN";
    
    map.setView([51.5074, -0.1278], 13);
    expandSidebar(); 
}

// Main Routing Execution
function calculateRoute() {
    const btn = document.getElementById('calc_btn');
    const startStr = document.getElementById('start_node').value;
    const targetStr = document.getElementById('target_node').value;
    
    if (!startStr || !targetStr) { alert("Please select valid stations from the search dropdown."); return; }

    const start_id = parseInt(startStr); const target_id = parseInt(targetStr);
    if (start_id === target_id) return;

    if (animTimer) clearInterval(animTimer);
    if (pathTimer) clearInterval(pathTimer);
    if (!map.hasLayer(baseNetworkLayer)) map.addLayer(baseNetworkLayer);

    btn.disabled = true;
    btn.innerText = "PROCESSING...";
    document.getElementById('itinerary').innerHTML = "Calculating optimal route...";
    clearMap();
    
    collapseSidebar(); 

    fetch('/api/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start: start_id, target: target_id })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('itinerary').innerHTML = data.itinerary;
        
        let frame = 0;
        const max_frames = Math.max(data.dijkstra.length, data.astar.length);
        const astar_set = new Set(data.astar.map(c => c.join(','))); 
        const transferMap = new Map();
        data.transfers.forEach(t => transferMap.set(t.coord.join(','), t));

        // Animate algorithm exploration
        animTimer = setInterval(() => {
            document.getElementById('stats').innerText = `${data.stats}`;

            [data.dijkstra, data.astar].forEach((list, idx) => {
                if (frame < list.length) {
                    const coord = list[frame];
                    const isAStar = (idx === 1);
                    if (!isAStar && astar_set.has(coord.join(','))) return;

                    const nodeInfo = stationLookup[coord.join(',')] || {name: "Unknown Node", lines: []};
                    let marker = L.circleMarker(coord, { radius: isAStar ? 5 : 4, color: isAStar ? '#4285f4' : '#d93025', fillColor: isAStar ? '#4285f4' : '#d93025', fillOpacity: isAStar ? 0.7 : 0.4, stroke: false })
                    .bindTooltip(createStationTooltip(nodeInfo), {direction: 'top', offset: [0, -10], className: 'custom-tooltip', sticky: true}).addTo(map);
                    
                    explorationLayers.push(marker);
                }
            });

            frame++;

            if (frame >= max_frames) {
                clearInterval(animTimer);
                
                btn.innerText = "TRACING PATH...";
                
                let pathLine = L.polyline([], {color: '#1a73e8', weight: 7, opacity: 0.9, className: 'path-glow'}).addTo(map);
                dynamicLayers.push(pathLine);

                let pFrame = 0;
                
                // Animate final optimal path
                pathTimer = setInterval(() => {
                    if (pFrame < data.path.length) {
                        const coord = data.path[pFrame];
                        pathLine.addLatLng(coord); 
                        
                        const coordKey = coord.join(',');
                        const isTransfer = transferMap.has(coordKey);
                        const nodeInfo = stationLookup[coordKey] || {name: "Unknown Node", lines: []};
                        
                        let tooltipHtml = createStationTooltip(nodeInfo);
                        
                        if (isTransfer) {
                            const tInfo = transferMap.get(coordKey);
                            const imgFrom = tInfo.from_logo ? `<img src="/static/line_logo/${tInfo.from_logo}">` : '';
                            const imgTo = tInfo.to_logo ? `<img src="/static/line_logo/${tInfo.to_logo}">` : '';
                            tooltipHtml += `
                                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(0,0,0,0.1); font-size: 11px;">
                                    <div style="margin-bottom: 4px; color: #5f6368; font-weight: bold;">🔄 REQUIRED ACTION:</div>
                                    Alight from: <span class="tooltip-line" style="background-color: ${tInfo.from_color}; margin: 2px 0; border-radius: 6px; padding: 4px 8px;">${imgFrom}${tInfo.from_line}</span><br>
                                    Transfer to: <span class="tooltip-line" style="background-color: ${tInfo.to_color}; margin: 2px 0; border-radius: 6px; padding: 4px 8px; display: inline-flex; margin-top: 4px;">${imgTo}${tInfo.to_line}</span>
                                </div>
                            `;
                        }

                        let pathNode = L.circleMarker(coord, { radius: isTransfer ? 7 : 5, color: isTransfer ? '#f29900' : '#1a73e8', weight: isTransfer ? 3 : 2, fillColor: '#ffffff', fillOpacity: 1 })
                        .bindTooltip(tooltipHtml, {direction: 'top', offset: [0, -10], className: 'custom-tooltip', sticky: true}).addTo(map);
                        
                        if (isTransfer) { pathNode.bringToFront(); }
                        dynamicLayers.push(pathNode);
                        
                        if (pFrame % 3 === 0 || pFrame === data.path.length - 1) {
                            map.panTo(coord, {animate: true, duration: 0.2});
                        }
                        
                        pFrame++;
                    } else {
                        clearInterval(pathTimer);
                        
                        const flash = document.getElementById('flash-overlay');
                        flash.style.transition = 'none';
                        flash.style.opacity = '0.9'; 
                        
                        setTimeout(() => {
                            map.removeLayer(baseNetworkLayer);
                            explorationLayers.forEach(layer => map.removeLayer(layer));
                            
                            flash.style.transition = 'opacity 0.8s ease-out';
                            flash.style.opacity = '0';
                            
                            const infographicHtml = `<div class="foglio-container"><strong class="foglio-title">🗺️ TRAVEL ITINERARY</strong><hr style="border:0.5px solid rgba(0,0,0,0.1); margin: 8px 0;">${data.itinerary}</div>`;
                            pathLine.bindTooltip(infographicHtml, {className: 'infographic-tooltip', sticky: true, opacity: 1});
                            
                            let m1 = L.marker(data.path[0], {icon: L.divIcon({className: 'pulse-marker-start', html: 'A', iconSize: [24, 24]})}).bindTooltip(`<strong style="font-size:14px; color:#1e8e3e;">ORIGIN</strong><br>${data.start_name}`, {direction: 'top', offset: [0, -10], className: 'custom-tooltip'}).addTo(map);
                            let m2 = L.marker(data.path[data.path.length-1], {icon: L.divIcon({className: 'pulse-marker-end', html: 'B', iconSize: [24, 24]})}).bindTooltip(`<strong style="font-size:14px; color:#d93025;">DESTINATION</strong><br>${data.target_name}`, {direction: 'top', offset: [0, -10], className: 'custom-tooltip'}).addTo(map);
                            dynamicLayers.push(m1, m2);

                            let padBottom = window.innerWidth <= 768 ? 150 : 50;
                            let padLeft = window.innerWidth <= 768 ? 50 : 420;
                            
                            map.fitBounds(pathLine.getBounds(), {paddingTopLeft: [padLeft, 50], paddingBottomRight: [50, padBottom], animate: true, duration: 1.0});
                            
                            btn.disabled = false;
                            btn.innerText = "INITIATE SCAN";
                            
                        }, 80); 
                    }
                }, 40); 
            }
        }, 10);
    });
}