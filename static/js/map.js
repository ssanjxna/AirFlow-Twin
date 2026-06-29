// Initialize map centered on Dubai Airport
const map = L.map('airport-map', { 
    zoomControl: false,
    minZoom: 13,
    maxZoom: 18
}).setView([25.2532, 55.3657], 15);

// Add dark mode map tiles
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { 
    maxZoom: 19,
    attribution: '© OpenStreetMap © CartoDB'
}).addTo(map);

// Add airport terminal buildings (simplified polygons)
const terminalBuildings = [
    [[25.2520, 55.3640], [25.2525, 55.3645], [25.2530, 55.3640], [25.2525, 55.3635]],
    [[25.2535, 55.3655], [25.2545, 55.3665], [25.2550, 55.3660], [25.2540, 55.3650]],
    [[25.2555, 55.3675], [25.2565, 55.3685], [25.2570, 55.3680], [25.2560, 55.3670]]
];

terminalBuildings.forEach(terminal => {
    L.polygon(terminal, {
        color: '#475569',
        fillColor: '#1e293b',
        fillOpacity: 0.6,
        weight: 2
    }).addTo(map).bindPopup('Terminal Building');
});

// Add runway lines
const runways = [
    [[25.2500, 55.3600], [25.2580, 55.3720]],
    [[25.2490, 55.3610], [25.2570, 55.3710]]
];

runways.forEach(runway => {
    L.polyline(runway, {
        color: '#64748b',
        weight: 4,
        opacity: 0.8,
        dashArray: '10, 10'
    }).addTo(map);
});

const socket = io();
const flightMarkers = {};
let currentTimeOffset = 0;
let selectedFlightId = null;

// Load initial data
fetch('/api/flights')
    .then(response => response.json())
    .then(data => {
        updateMapDisplay(data);
        updateResourceStatus(data.resources);
    })
    .catch(error => {
        console.error('Error loading flights:', error);
    });

socket.on('update_map', function(data) {
    updateMapDisplay(data);
    updateHighRiskCount(data.flights);
});

function updateMapDisplay(data) {
    const flightList = document.getElementById('flight-list');
    if (!flightList) return;
    
    flightList.innerHTML = ''; 
    let highRiskCount = 0;

    data.flights.forEach(flight => {
        // Determine color based on risk
        let color = flight.risk > 70 ? '#ef4444' : (flight.risk > 40 ? '#f97316' : '#22c55e');
        let riskLevel = flight.risk > 70 ? 'HIGH' : (flight.risk > 40 ? 'MEDIUM' : 'LOW');
        
        // Create custom marker with plane icon
        if (!flightMarkers[flight.id]) {
            const markerHtml = `
                <div class="flight-marker" style="
                    width: 30px;
                    height: 30px;
                    background: ${color};
                    border: 3px solid white;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 14px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
                    cursor: pointer;
                    transition: transform 0.2s;
                " onmouseover="this.style.transform='scale(1.2)'" onmouseout="this.style.transform='scale(1)'">
                ✈️
                </div>
            `;
            
            const icon = L.divIcon({
                html: markerHtml,
                className: 'custom-marker',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });
            
            flightMarkers[flight.id] = L.marker([flight.lat, flight.lng], { icon: icon })
                .addTo(map)
                .bindPopup(`
                    <div style="min-width: 200px; font-family: sans-serif;">
                        <h3 style="margin: 0 0 8px 0; color: #1e293b; font-size: 16px;">${flight.id}</h3>
                        <p style="margin: 4px 0; font-size: 13px;"><strong>Route:</strong> ${flight.origin} → ${flight.destination}</p>
                        <p style="margin: 4px 0; font-size: 13px;"><strong>Gate:</strong> ${flight.gate}</p>
                        <p style="margin: 4px 0; font-size: 13px;"><strong>Status:</strong> ${flight.status}</p>
                        <p style="margin: 4px 0; font-size: 13px;"><strong>Risk:</strong> <span style="color: ${color}; font-weight: bold;">${flight.risk}%</span></p>
                        <p style="margin: 4px 0; font-size: 13px;"><strong>Aircraft:</strong> ${flight.aircraft_type || 'A320'}</p>
                        <button onclick="selectFlightFromPopup('${flight.id}')" style="
                            margin-top: 8px;
                            padding: 6px 12px;
                            background: #3b82f6;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            cursor: pointer;
                            font-size: 12px;
                        ">View Details</button>
                    </div>
                `);
            
            // Add click handler
            flightMarkers[flight.id].on('click', function() {
                selectFlight(flight.id);
            });
        } else {
            // Update existing marker
            flightMarkers[flight.id].setLatLng([flight.lat, flight.lng]);
            const markerElement = flightMarkers[flight.id].getElement();
            if (markerElement) {
                const innerDiv = markerElement.querySelector('div');
                if (innerDiv) {
                    innerDiv.style.background = color;
                }
            }
        }

        // Add to flight list
        let riskColor = flight.risk > 70 ? 'text-red-400 bg-red-400/10' : (flight.risk > 40 ? 'text-orange-400 bg-orange-400/10' : 'text-green-400 bg-green-400/10');
        let riskBadge = flight.risk > 70 ? 'HIGH RISK' : (flight.risk > 40 ? 'MEDIUM RISK' : 'LOW RISK');
        
        if (flight.risk > 70) highRiskCount++;
        
        const flightItem = document.createElement('div');
        flightItem.className = `flight-item flex justify-between items-center p-3 rounded border border-slate-700 mb-2 cursor-pointer hover:bg-slate-700 transition ${selectedFlightId === flight.id ? 'bg-slate-700 border-blue-500' : 'bg-slate-800'}`;
        flightItem.onclick = () => selectFlight(flight.id);
        flightItem.innerHTML = `
            <div>
                <div class="flex items-center gap-2">
                    <span class="font-bold text-sm">${flight.id}</span>
                    <span class="text-xs text-slate-400">${flight.status}</span>
                </div>
                <div class="text-xs text-slate-500 mt-1">${flight.origin} → ${flight.destination}</div>
            </div>
            <div class="text-right">
                <span class="text-xs font-bold px-2 py-1 rounded ${riskColor}">${flight.risk}%</span>
                <div class="text-xs text-slate-500 mt-1">${riskBadge}</div>
            </div>
        `;
        flightList.appendChild(flightItem);
    });
    
    // Update high risk count
    document.getElementById('high-risk-count').textContent = highRiskCount;
}

function updateHighRiskCount(flights) {
    const highRiskCount = flights.filter(f => f.risk > 70).length;
    document.getElementById('high-risk-count').textContent = highRiskCount;
}

function updateResourceStatus(resources) {
    if (resources) {
        document.getElementById('crew-status').textContent = `${resources.available_crews || 3}/${resources.maintenance_crews || 5}`;
        document.getElementById('truck-status').textContent = `${resources.available_trucks || 1}/${resources.fuel_trucks || 3}`;
        document.getElementById('baggage-status').textContent = `${resources.available_carts || 2}/${resources.baggage_carts || 4}`;
    }
}

// Time slider functionality
const timeSlider = document.getElementById('time-slider');
if (timeSlider) {
    timeSlider.addEventListener('input', function(e) {
        const minutes = parseInt(e.target.value);
        currentTimeOffset = minutes;
        
        // Update visual labels
        document.querySelectorAll('.time-label').forEach(el => {
            el.classList.remove('text-blue-400', 'font-bold');
        });
        
        const activeLabel = document.querySelector(`[data-time="${minutes}"]`);
        if (activeLabel) {
            activeLabel.classList.add('text-blue-400', 'font-bold');
        }
        
        // Update current time display
        const hours = 9;
        const mins = minutes;
        document.getElementById('current-time').textContent = `${hours}:${mins.toString().padStart(2, '0')}`;
        
        // Fetch future simulation
        fetch('/api/simulate_future', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ minutes: minutes })
        })
        .then(response => response.json())
        .then(data => {
            updateMapDisplay(data);
            if (data.metrics) {
                updateAIMetrics(data.metrics);
            }
        })
        .catch(error => {
            console.error('Error simulating future:', error);
        });
    });
}

function updateAIMetrics(metrics) {
    if (metrics) {
        document.getElementById('before-delayed').textContent = metrics.flights_delayed_before;
        document.getElementById('after-delayed').textContent = Math.max(0, metrics.flights_delayed_after);
        
        const beforeMinutes = metrics.total_delay_before;
        const afterMinutes = metrics.total_delay_after;
        const prevented = beforeMinutes - afterMinutes;
        
        document.getElementById('before-total-delay').textContent = formatDuration(beforeMinutes);
        document.getElementById('after-total-delay').textContent = formatDuration(afterMinutes);
        document.getElementById('total-prevented').textContent = formatDuration(prevented);
        document.getElementById('prevented-delay').textContent = formatDuration(prevented);
    }
}

function formatDuration(minutes) {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
}

// Flight selection
function selectFlight(flightId) {
    selectedFlightId = flightId;
    
    fetch(`/api/get_recommendation/${flightId}`)
        .then(response => response.json())
        .then(data => {
            displayFlightDetails(data);
        })
        .catch(error => {
            console.error('Error fetching recommendation:', error);
        });
}

function selectFlightFromPopup(flightId) {
    selectFlight(flightId);
    if (flightMarkers[flightId]) {
        map.openPopup(flightMarkers[flightId].getPopup());
    }
}

function displayFlightDetails(data) {
    const card = document.getElementById('selected-flight-card');
    if (!card) return;
    
    card.classList.remove('hidden');
    
    document.getElementById('selected-flight-id').textContent = data.flight_id;
    document.getElementById('selected-flight-route').textContent = `${data.flight_data.origin} → ${data.flight_data.destination}`;
    document.getElementById('selected-gate').textContent = data.flight_data.gate;
    document.getElementById('selected-aircraft').textContent = data.flight_data.aircraft_type || 'A320';
    document.getElementById('selected-status').textContent = data.flight_data.status;
    document.getElementById('selected-delay').textContent = `${data.flight_data.delay_minutes || 0} min`;
    
    const riskElement = document.getElementById('selected-risk-score');
    riskElement.textContent = `${data.risk}/100`;
    
    if (data.risk > 70) {
        riskElement.className = 'bg-red-500/20 text-red-400 text-xs px-3 py-1 rounded-full font-bold';
    } else if (data.risk > 40) {
        riskElement.className = 'bg-orange-500/20 text-orange-400 text-xs px-3 py-1 rounded-full font-bold';
    } else {
        riskElement.className = 'bg-green-500/20 text-green-400 text-xs px-3 py-1 rounded-full font-bold';
    }
    
    document.getElementById('ai-recommendation-text').innerHTML = data.recommendation;
    
    // Reset apply button
    const applyBtn = document.getElementById('apply-btn');
    applyBtn.textContent = 'Apply Recommendation';
    applyBtn.disabled = false;
    applyBtn.classList.remove('bg-green-600');
    applyBtn.classList.add('bg-blue-600');
    
    // Update flight list highlighting
    document.querySelectorAll('.flight-item').forEach(item => {
        item.classList.remove('bg-slate-700', 'border-blue-500');
        if (item.textContent.includes(data.flight_id)) {
            item.classList.add('bg-slate-700', 'border-blue-500');
        }
    });
}

function applyRecommendation() {
    if (!selectedFlightId) return;
    
    const btn = document.getElementById('apply-btn');
    btn.textContent = 'Applying...';
    btn.disabled = true;
    
    fetch(`/api/apply_recommendation/${selectedFlightId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        btn.textContent = 'Applied Successfully! ✓';
        btn.classList.remove('bg-blue-600');
        btn.classList.add('bg-green-600');
        
        // Update risk score display
        const riskElement = document.getElementById('selected-risk-score');
        const currentRisk = parseInt(riskElement.textContent);
        const newRisk = Math.max(0, currentRisk - data.risk_reduction);
        riskElement.textContent = `${newRisk}/100`;
        riskElement.classList.remove('bg-red-500/20', 'text-red-400');
        riskElement.classList.add('bg-green-500/20', 'text-green-400');
        
        // Update prevented delay
        const preventedElement = document.getElementById('total-prevented');
        const currentPrevented = parseInt(preventedElement.textContent);
        preventedElement.textContent = `${currentPrevented + data.delay_prevented}m`;
        
        setTimeout(() => {
            btn.textContent = 'Apply Recommendation';
            btn.disabled = false;
            btn.classList.remove('bg-green-600');
            btn.classList.add('bg-blue-600');
        }, 3000);
    })
    .catch(error => {
        console.error('Error applying recommendation:', error);
        btn.textContent = 'Error - Try Again';
        btn.disabled = false;
    });
}

window.selectFlight = selectFlight;
window.selectFlightFromPopup = selectFlightFromPopup;
window.applyRecommendation = applyRecommendation;