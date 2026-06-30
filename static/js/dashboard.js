// Map Coordinates
const hotspotPositions = {
    'UK-633': { x: 31, y: 8 },
    'BA-6017': { x: 60, y: 18 },
    'BA-7303': { x: 94, y: 40 },
    'KL-7243': { x: 44, y: 14 },
    'SG-1280': { x: 77, y: 27 },
    'PARKING': { x: 27, y: 77 } 
};

// Scenario Engine
const futureScenarios = {
    0: {
        events: [],
        message: "Current state: Normal operations.",
        modifiers: {},
        newFlights: []
    },
    10: {
        events: [
            { 
                time: '+5m', 
                text: 'BA-6017 taxiing to gate', 
                type: 'info',
                risk: 65,
                relatedFlightId: 'BA-6017', // Link to flight
                impact: 'Minor delay risk due to gate assignment',
                recommendations: [
                    { id: 'evt_rec1', text: 'Assign Gate B3 (closest available)', impact: '-5m delay', riskReduction: 10, delayReduction: 5 },
                    { id: 'evt_rec2', text: 'Pre-position baggage team at Gate B3', impact: '-3m delay', riskReduction: 5, delayReduction: 3 }
                ]
            }
        ],
        message: "Minor ground movements expected.",
        modifiers: { 'BA-6017': { risk: 65, delay: 32 } },
        newFlights: []
    },
    30: {
        events: [
            { 
                time: '+15m', 
                text: '⚠️ Maintenance Crew Shift Change', 
                type: 'warning',
                risk: 75,
                relatedFlightId: 'SG-1280', // Link to flight
                impact: 'Crew 2 leaving, Crew 3 not yet arrived. SG-1280 maintenance incomplete.',
                recommendations: [
                    { id: 'evt_rec1', text: 'Delay Crew 2 departure by 45 minutes', impact: '-20m delay', riskReduction: 25, delayReduction: 20 },
                    { id: 'evt_rec2', text: 'Pre-authorize Crew 3 overtime', impact: '-15m delay', riskReduction: 20, delayReduction: 15 },
                    { id: 'evt_rec3', text: 'Reassign Crew 1 from completed flight', impact: '-10m delay', riskReduction: 15, delayReduction: 10 }
                ]
            },
            { 
                time: '+25m', 
                text: '✈️ New Arrival: EK-9988 (A380)', 
                type: 'critical',
                risk: 85,
                relatedFlightId: 'EK-9988', // Link to flight
                impact: 'Large aircraft arriving during shift change. Limited ground crew available.',
                recommendations: [
                    { id: 'evt_rec1', text: 'Pre-assign Crew B before shift change completes', impact: '-20m delay', riskReduction: 25, delayReduction: 20 },
                    { id: 'evt_rec2', text: 'Route to Gate A4 (closest to active crew)', impact: '-12m delay', riskReduction: 15, delayReduction: 12 },
                    { id: 'evt_rec3', text: 'Priority baggage handling team allocation', impact: '-8m delay', riskReduction: 10, delayReduction: 8 }
                ]
            },
            { 
                time: '+28m', 
                text: 'Parking capacity reaches 85%', 
                type: 'warning',
                risk: 70,
                relatedFlightId: null, // No specific flight
                impact: 'Incoming passenger vehicles will cause congestion at terminal access.',
                recommendations: [
                    { id: 'evt_rec1', text: 'Open overflow parking P3 and P4 immediately', impact: '-30% congestion', riskReduction: 30, delayReduction: 15 },
                    { id: 'evt_rec2', text: 'Activate dynamic signage to redirect traffic', impact: '-20% congestion', riskReduction: 20, delayReduction: 10 }
                ]
            }
        ],
        message: "Risk increasing due to crew shift change and incoming traffic.",
        modifiers: { 'BA-6017': { risk: 75, delay: 35 }, 'SG-1280': { risk: 85, delay: 45 } },
        newFlights: [{ id: 'EK-9988', origin: 'DXB', destination: 'LHR', risk: 85, delay: 45 }]
    },
    60: {
        events: [
            { 
                time: '+40m', 
                text: '⛈️ Weather Warning: Heavy rain at DOH', 
                type: 'critical',
                risk: 92,
                relatedFlightId: 'EK-9988',
                impact: 'Flights from Doha delayed. Ground operations slowed by 40%.',
                recommendations: [
                    { id: 'evt_rec1', text: 'Reroute DOH flights to alternate gates', impact: '-25m delay', riskReduction: 30, delayReduction: 25 },
                    { id: 'evt_rec2', text: 'Deploy additional ground staff', impact: '-15m delay', riskReduction: 20, delayReduction: 15 }
                ]
            }
        ],
        message: "Severe weather impacting incoming flights.",
        modifiers: { 'EK-9988': { risk: 92, delay: 60 } },
        newFlights: []
    }
};

const riskForecasts = {
    'UK-633': [61, 63, 70, 75], 'BA-6017': [61, 65, 75, 82], 'BA-7303': [61, 62, 68, 74],
    'KL-7243': [36, 38, 45, 52], 'SG-1280': [80, 82, 85, 88], 'EK-9988': [0, 0, 85, 92], 'PARKING': [60, 65, 75, 85]
};

const recommendationsDB = {
    'SG-1280': [
        { id: 'rec1', text: 'Reassign maintenance crew from KL-7243', impact: '-15m delay, -20% risk', riskReduction: 20, delayReduction: 15 },
        { id: 'rec2', text: 'Open Overflow Parking P3', impact: '-8m delay, -10% risk', riskReduction: 10, delayReduction: 8 }
    ],
    'EK-9988': [
        { id: 'rec1', text: 'Pre-assign Crew B', impact: '-20m delay, -25% risk', riskReduction: 25, delayReduction: 20 }
    ],
    'PARKING': [
        { id: 'rec1', text: 'Open overflow parking P3 and P4', impact: '-30% congestion', riskReduction: 30, delayReduction: 15 },
        { id: 'rec2', text: 'Activate dynamic signage', impact: '-20% congestion', riskReduction: 20, delayReduction: 10 }
    ],
    'default': [
        { id: 'rec1', text: 'Reassign maintenance crew', impact: '-12m delay, -15% risk', riskReduction: 15, delayReduction: 12 }
    ]
};

let selectedFlightId = null;
let currentTimeStep = 0;
let selectedRecommendations = new Set();
let currentFlights = [];
let parkingUpdateInterval;
let currentParkingData = null;
let appliedRecommendations = new Set();
let currentRiskValue = 0;
let currentContext = null;
let currentEventIndex = null;

async function initDashboard() {
    await loadAndRenderData();
    await updateParkingStatus();
    setupTimeControls();
    updateCurrentTime();
    parkingUpdateInterval = setInterval(updateParkingStatus, 30000);
    setInterval(updateCurrentTime, 1000);
}

async function loadAndRenderData() {
    try {
        const response = await fetch('/api/flights');
        const baseData = await response.json();
        let flights = baseData.flights.filter(f => hotspotPositions[f.id]).slice(0, 5);
        
        const scenario = futureScenarios[currentTimeStep];
        if (scenario.modifiers) {
            flights = flights.map(f => scenario.modifiers[f.id] ? { ...f, ...scenario.modifiers[f.id] } : f);
        }
        if (scenario.newFlights) {
            scenario.newFlights.forEach(newF => { if (!flights.find(f => f.id === newF.id)) flights.push(newF); });
        }
        
        currentFlights = flights;
        updateEventTimeline(scenario);
        updateRiskForecast();
        renderHotspots(flights);
        renderFlightRiskTable(flights);
        updateHighRiskCount(flights);
    } catch (error) { console.error('Error loading data:', error); }
}

function renderHotspots(flights) {
    const container = document.getElementById('hotspots-container');
    if (!container) return;
    container.innerHTML = '';

    flights.forEach(flight => {
        if (!hotspotPositions[flight.id]) return;
        const pos = hotspotPositions[flight.id];
        let riskClass = getRiskClass(flight.risk);

        const hotspot = document.createElement('div');
        hotspot.className = 'hotspot ' + riskClass;
        hotspot.style.left = pos.x + '%';
        hotspot.style.top = pos.y + '%';
        
        const marker = document.createElement('div');
        marker.className = 'hotspot-marker';
        hotspot.appendChild(marker);
        
        const label = document.createElement('div');
        label.className = 'hotspot-label';
        label.innerHTML = `<span class="flight-id">${flight.id}</span><span class="risk-text">${flight.risk}% Risk</span>`;
        hotspot.appendChild(label);
        hotspot.onclick = (e) => { e.stopPropagation(); selectFlight(flight); };
        container.appendChild(hotspot);
    });

    const parkingPos = hotspotPositions['PARKING'];
    if (parkingPos) {
        const zone = document.createElement('div');
        zone.id = 'parking-zone';
        zone.className = 'parking-zone';
        zone.style.left = parkingPos.x + '%';
        zone.style.top = parkingPos.y + '%';
        zone.style.width = '250px';
        zone.style.height = '180px';
        
        const parkingRisk = currentParkingData ? Math.round(currentParkingData.congestion_score) : 60;
        const label = document.createElement('div');
        label.className = 'parking-label';
        label.id = 'parking-zone-label';
        label.innerHTML = parkingRisk >= 80 ? ' PARKING CONGESTION RISK' : (parkingRisk >= 50 ? '⚠️ PARKING WARNING' : '✅ PARKING - NORMAL');
        zone.appendChild(label);
        zone.onclick = (e) => { e.stopPropagation(); showParkingDetails(); };
        container.appendChild(zone);
    }
}

function renderFlightRiskTable(flights) {
    const tbody = document.getElementById('flight-risk-table');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    // Sort: CRITICAL first, then HIGH, then NORMAL
    const sortedFlights = [...flights].sort((a, b) => b.risk - a.risk);

    sortedFlights.forEach((flight) => {
        let riskColor = getRiskColor(flight.risk);
        let riskBg = getRiskBg(flight.risk);
        let delay = flight.delay_minutes || Math.floor(flight.risk * 0.5);
        let priority = getPriorityLabel(flight.risk);
        let priorityClass = getPriorityClass(flight.risk);

        const row = document.createElement('tr');
        row.className = 'flight-row border-b border-slate-800 hover:bg-slate-800/50 transition cursor-pointer';
        if (selectedFlightId === flight.id) row.classList.add('bg-slate-800/70');
        
        row.innerHTML = `
            <td class="py-3"><div class="flex items-center gap-2"><span class="text-xs font-bold px-2 py-1 rounded border ${priorityClass}">${priority}</span><span class="font-bold text-white">${flight.id}</span></div></td>
            <td class="py-3 text-slate-400">${flight.origin} → ${flight.destination}</td>
            <td class="py-3 text-right ${riskColor} font-medium">${delay}m</td>
            <td class="py-3 text-right"><div class="flex items-center justify-end gap-2"><div class="w-16 h-2 bg-slate-700 rounded-full overflow-hidden"><div class="h-full ${riskBg} rounded-full" style="width: ${flight.risk}%"></div></div><span class="font-bold ${riskColor} w-10 text-right">${flight.risk}%</span></div></td>
        `;
        row.onclick = () => selectFlight(flight);
        tbody.appendChild(row);
    });
}

function getRiskClass(risk) { if (risk >= 80) return 'high-risk'; if (risk >= 50) return 'medium-risk'; return 'low-risk'; }
function getRiskColor(risk) { if (risk >= 80) return 'text-red-500'; if (risk >= 50) return 'text-orange-500'; return 'text-green-500'; }
function getRiskBg(risk) { if (risk >= 80) return 'bg-red-500'; if (risk >= 50) return 'bg-orange-500'; return 'bg-green-500'; }
function getPriorityLabel(risk) { if (risk >= 80) return 'CRITICAL'; if (risk >= 50) return 'HIGH'; return 'NORMAL'; }
function getPriorityClass(risk) { if (risk >= 80) return 'bg-red-500/20 text-red-400 border-red-500/30'; if (risk >= 50) return 'bg-orange-500/20 text-orange-400 border-orange-500/30'; return 'bg-green-500/20 text-green-400 border-green-500/30'; }
function getBadgeClass(risk) { if (risk >= 80) return 'bg-red-600'; if (risk >= 50) return 'bg-orange-600'; return 'bg-green-600'; }

async function selectFlight(flight) {
    currentContext = 'flight';
    currentEventIndex = null;
    selectedFlightId = flight.id;
    selectedRecommendations.clear();
    appliedRecommendations.clear();
    currentRiskValue = flight.risk;
    
    document.getElementById('default-state').classList.add('hidden');
    document.getElementById('selected-flight-card').classList.remove('hidden');
    
    document.getElementById('selected-flight-id').textContent = flight.id;
    document.getElementById('selected-flight-route').textContent = `${flight.origin} → ${flight.destination}`;
    
    updateAIPanelUI(flight.risk, flight.delay_minutes || Math.floor(flight.risk * 0.5));
    document.getElementById('risk-cause').textContent = "Aircraft maintenance delay and high predicted passenger arrival time due to landside traffic.";
    renderRecommendationCards(flight);
    updateExpectedImpact();
    updateApplyButton();
}

function updateAIPanelUI(risk, delay) {
    const riskColor = getRiskColor(risk);
    const badgeClass = getBadgeClass(risk);
    const riskText = getPriorityLabel(risk);
    
    const badge = document.getElementById('risk-badge');
    if (badge) { badge.textContent = riskText; badge.className = `px-2 py-1 ${badgeClass} text-white text-xs font-bold rounded uppercase`; }
    
    const scoreEl = document.getElementById('risk-score-value');
    if (scoreEl) { scoreEl.textContent = risk; scoreEl.className = `text-2xl font-bold ${riskColor}`; }
    
    const riskCircle = document.getElementById('risk-circle');
    if (riskCircle) {
        riskCircle.setAttribute('stroke', risk >= 80 ? '#ef4444' : (risk >= 50 ? '#f97316' : '#22c55e'));
    }
    
    document.getElementById('predicted-delay').textContent = delay + 'm';
    document.getElementById('confidence').textContent = Math.floor(80 + Math.random() * 15) + '%';
}

function renderRecommendationCards(item) {
    const container = document.getElementById('ai-recommendations');
    if (!container) return;
    container.innerHTML = '';
    
    let recs;
    if (currentContext === 'event' && currentEventIndex !== null) {
        recs = futureScenarios[currentTimeStep].events[currentEventIndex].recommendations || [];
    } else {
        recs = recommendationsDB[item.id] || recommendationsDB['default'];
    }
    
    recs.forEach(rec => {
        if (appliedRecommendations.has(rec.id)) return;
        const card = document.createElement('div');
        card.className = 'rec-card';
        card.dataset.recId = rec.id;
        card.onclick = () => toggleRecommendation(rec.id, card);
        card.innerHTML = `<div class="rec-checkbox"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg></div><div class="rec-content"><div class="rec-text">${rec.text}</div><div class="rec-impact">${rec.impact}</div></div>`;
        container.appendChild(card);
    });
}

function showParkingDetails() {
    currentContext = 'parking';
    currentEventIndex = null;
    selectedFlightId = 'PARKING';
    selectedRecommendations.clear();
    appliedRecommendations.clear();
    
    document.getElementById('default-state').classList.add('hidden');
    document.getElementById('selected-flight-card').classList.remove('hidden');
    document.getElementById('selected-flight-id').textContent = 'PARKING';
    document.getElementById('selected-flight-route').textContent = 'Landside → Terminal';
    
    const risk = currentParkingData ? Math.round(currentParkingData.congestion_score) : 60;
    currentRiskValue = risk;
    updateAIPanelUI(risk, Math.round(risk * 0.25));
    document.getElementById('risk-cause').textContent = `Passenger parking congestion at ${risk}%.`;
    renderRecommendationCards({ id: 'PARKING' });
    updateExpectedImpact();
    updateApplyButton();
}

async function updateParkingStatus() {
    try {
        const response = await fetch('/api/parking_status');
        currentParkingData = await response.json();
        updateParkingZoneOnMap(currentParkingData);
    } catch (error) { console.error('Error fetching parking status:', error); }
}

function updateParkingZoneOnMap(parkingData) {
    let zone = document.getElementById('parking-zone');
    if (!zone) return;
    const score = parkingData.congestion_score;
    let borderColor = score >= 80 ? '#ef4444' : (score >= 50 ? '#f97316' : '#22c55e');
    zone.style.borderColor = borderColor;
    zone.style.background = `radial-gradient(circle, ${borderColor}30 0%, transparent 70%)`;
    zone.style.boxShadow = `0 0 50px ${borderColor}80`;
    
    const label = document.getElementById('parking-zone-label');
    if (label) label.innerHTML = score >= 80 ? '🚨 PARKING CONGESTION RISK' : (score >= 50 ? '⚠️ PARKING WARNING' : '✅ PARKING - NORMAL');
}

function showEventDetails(eventIndex) {
    currentContext = 'event';
    currentEventIndex = eventIndex;
    selectedRecommendations.clear();
    appliedRecommendations.clear();
    
    const scenario = futureScenarios[currentTimeStep];
    const event = scenario.events[eventIndex];
    
    document.getElementById('default-state').classList.add('hidden');
    document.getElementById('selected-flight-card').classList.remove('hidden');
    
    document.getElementById('selected-flight-id').innerHTML = `<div class="event-header-title">${event.text}</div>`;
    document.getElementById('selected-flight-route').innerHTML = `<span class="event-header-time">${event.time} • ${event.type.toUpperCase()}</span>`;
    
    currentRiskValue = event.risk;
    updateAIPanelUI(event.risk, Math.floor(event.risk * 0.5));
    document.getElementById('risk-cause').innerHTML = `<div class="event-impact-box"><div class="event-impact-label">Impact Assessment</div><div class="event-impact-text">${event.impact}</div></div>`;
    
    renderRecommendationCards({ id: 'event' });
    updateExpectedImpact();
    updateApplyButton();
}

function toggleRecommendation(recId, cardElement) {
    if (selectedRecommendations.has(recId)) { selectedRecommendations.delete(recId); cardElement.classList.remove('selected'); }
    else { selectedRecommendations.add(recId); cardElement.classList.add('selected'); }
    updateExpectedImpact();
    updateApplyButton();
}

function selectAllRecommendations() {
    document.querySelectorAll('.rec-card').forEach(card => { selectedRecommendations.add(card.dataset.recId); card.classList.add('selected'); });
    updateExpectedImpact();
    updateApplyButton();
}

function updateExpectedImpact() {
    let recs = (currentContext === 'event' && currentEventIndex !== null) ? futureScenarios[currentTimeStep].events[currentEventIndex].recommendations : (recommendationsDB[selectedFlightId] || recommendationsDB['default']);
    let totalRiskReduction = 0, totalDelayReduction = 0;
    selectedRecommendations.forEach(recId => { const rec = recs.find(r => r.id === recId); if (rec) { totalRiskReduction += rec.riskReduction; totalDelayReduction += rec.delayReduction; } });
    
    const currentRisk = currentRiskValue || 80;
    const currentDelay = parseInt(document.getElementById('predicted-delay').textContent) || 40;
    
    document.getElementById('expected-risk-after').textContent = Math.max(0, currentRisk - totalRiskReduction) + '%';
    document.getElementById('expected-delay-reduction').textContent = totalDelayReduction + 'm';
}

function updateApplyButton() {
    const btn = document.getElementById('apply-btn');
    if (!btn) return;
    btn.disabled = selectedRecommendations.size === 0;
    btn.textContent = selectedRecommendations.size === 0 ? 'Select at least one recommendation' : `Apply ${selectedRecommendations.size} Recommendation${selectedRecommendations.size > 1 ? 's' : ''}`;
}

async function applySelectedRecommendations() {
    const btn = document.getElementById('apply-btn');
    if (!btn) return;
    btn.textContent = 'Applying...';
    btn.disabled = true;
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    let recs = (currentContext === 'event' && currentEventIndex !== null) ? futureScenarios[currentTimeStep].events[currentEventIndex].recommendations : (recommendationsDB[selectedFlightId] || recommendationsDB['default']);
    let totalRiskReduction = 0, totalDelayReduction = 0;
    
    selectedRecommendations.forEach(recId => { const rec = recs.find(r => r.id === recId); if (rec) { totalRiskReduction += rec.riskReduction; totalDelayReduction += rec.delayReduction; appliedRecommendations.add(recId); } });
    
    const newRisk = Math.max(0, currentRiskValue - totalRiskReduction);
    const newDelay = Math.max(0, parseInt(document.getElementById('predicted-delay').textContent) - totalDelayReduction);
    currentRiskValue = newRisk;
    
    // 1. UPDATE EVENT RISK (For Prediction Horizon filtering)
    if (currentContext === 'event' && currentEventIndex !== null) {
        futureScenarios[currentTimeStep].events[currentEventIndex].risk = newRisk;
        
        // 2. UPDATE RELATED FLIGHT RISK (For Flight Risk List downgrading)
        const eventId = futureScenarios[currentTimeStep].events[currentEventIndex].relatedFlightId;
        if (eventId) {
            const flightIndex = currentFlights.findIndex(f => f.id === eventId);
            if (flightIndex !== -1) {
                currentFlights[flightIndex].risk = newRisk;
                currentFlights[flightIndex].delay_minutes = newDelay;
            }
        }
    }
    
    updateAIPanelUI(newRisk, newDelay);
    
    const causeEl = document.getElementById('risk-cause');
    if (causeEl) {
        if (currentContext === 'event') {
            causeEl.textContent = `Event mitigated. Risk reduced to ${newRisk}%. ${newRisk < 50 ? 'Status: NORMAL/UPCOMING.' : 'Status: HIGH.'}`;
        } else if (selectedFlightId === 'PARKING') {
            causeEl.textContent = `Parking congestion reduced to ${newRisk}%.`;
        } else {
            causeEl.textContent = `Flight risk reduced to ${newRisk}%.`;
        }
    }
    
    // Refresh UI
    if (currentContext === 'flight') {
        renderHotspots(currentFlights);
        renderFlightRiskTable(currentFlights);
        updateHighRiskCount(currentFlights);
    } else if (currentContext === 'event') {
        // Update event timeline (will filter out if risk < 50)
        updateEventTimeline(futureScenarios[currentTimeStep]);
        // Update flight table (will show downgraded status)
        renderFlightRiskTable(currentFlights);
        updateHighRiskCount(currentFlights);
        renderHotspots(currentFlights);
    } else if (currentContext === 'parking' && currentParkingData) {
        currentParkingData.congestion_score = newRisk;
        updateParkingZoneOnMap(currentParkingData);
    }
    
    btn.textContent = '✓ Applied Successfully!';
    btn.classList.add('success');
    selectedRecommendations.clear();
    
    setTimeout(() => {
        renderRecommendationCards({ id: currentContext === 'event' ? 'event' : selectedFlightId });
        updateApplyButton();
    }, 100);
    
    setTimeout(() => {
        btn.textContent = 'Select at least one recommendation';
        btn.classList.remove('success');
        btn.disabled = false;
    }, 2000);
}

function setupTimeControls() {
    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.onclick = function() {
            document.querySelectorAll('.time-btn').forEach(b => { b.classList.remove('bg-blue-600', 'text-white'); b.classList.add('bg-slate-800', 'text-slate-400'); });
            this.classList.remove('bg-slate-800', 'text-slate-400');
            this.classList.add('bg-blue-600', 'text-white');
            currentTimeStep = parseInt(this.dataset.time);
            loadAndRenderData();
        };
    });
}

function toggleRiskForecast() {
    const forecast = document.getElementById('risk-forecast-floating');
    const btn = event.target;
    if (forecast.classList.contains('hidden')) { forecast.classList.remove('hidden'); btn.textContent = 'Hide Forecast'; }
    else { forecast.classList.add('hidden'); btn.textContent = 'Show Forecast'; }
}

function updateEventTimeline(scenario) {
    const timeline = document.getElementById('event-timeline');
    if (!timeline) return;
    timeline.innerHTML = '';
    
    // FILTER: Only show events with risk >= 50 (CRITICAL or HIGH)
    // Events with risk < 50 (NORMAL) will DISAPPEAR from this list
    const eventsToShow = scenario.events.filter(evt => evt.risk >= 50);
    
    if (eventsToShow.length === 0) {
        timeline.innerHTML = `<div class="event-item info"><span class="event-time">--</span><span class="event-text">No upcoming critical events.</span></div>`;
    } else {
        eventsToShow.forEach((evt, index) => {
            // Find original index for onclick
            const originalIndex = scenario.events.indexOf(evt);
            
            const div = document.createElement('div');
            let itemClass = evt.risk >= 80 ? 'critical' : 'warning';
            
            div.className = `event-item ${itemClass}`;
            div.innerHTML = `
                <span class="event-time">${evt.time}</span>
                <div class="flex flex-col flex-1">
                    <span class="event-text font-bold">${evt.text}</span>
                    <span class="text-[9px] ${getRiskColor(evt.risk)} font-bold mt-0.5">${evt.risk >= 80 ? 'CRITICAL' : 'HIGH'} • ${evt.risk}% Risk</span>
                </div>
                <button class="event-action-btn" onclick="showEventDetails(${originalIndex})">View AI Analysis</button>
            `;
            timeline.appendChild(div);
        });
    }
    
    const msgDiv = document.getElementById('prediction-message');
    if (msgDiv) msgDiv.textContent = scenario.message || 'Viewing current state.';
}

function updateRiskForecast() {
    const flightId = selectedFlightId || 'SG-1280';
    const forecast = riskForecasts[flightId] || [60, 65, 75, 85];
    const bars = [{ id: 'bar-now', value: forecast[0], label: 'risk-now-label' }, { id: 'bar-10', value: forecast[1], label: 'risk-10-label' }, { id: 'bar-30', value: forecast[2], label: 'risk-30-label' }, { id: 'bar-60', value: forecast[3], label: 'risk-60-label' }];
    
    bars.forEach(bar => {
        const element = document.getElementById(bar.id);
        const labelElement = document.getElementById(bar.label);
        if (element) {
            element.style.height = Math.max(bar.value, 10) + '%';
            element.className = `w-full rounded-t-lg transition-all duration-500 ${bar.value >= 80 ? 'bg-red-600' : (bar.value >= 50 ? 'bg-orange-500' : 'bg-green-500')}`;
        }
        if (labelElement) labelElement.textContent = bar.value + '%';
    });
}

function updateCurrentTime() { document.getElementById('current-time').textContent = new Date().toTimeString().split(' ')[0]; }
function updateHighRiskCount(flights) { document.getElementById('high-risk-count').textContent = flights.filter(f => f.risk >= 80).length; }
function toggleAIImpact() { const modal = document.getElementById('ai-impact-modal'); const backdrop = document.getElementById('modal-backdrop'); if (modal.classList.contains('active')) { modal.classList.remove('active'); backdrop.classList.remove('active'); } else { modal.classList.add('active'); backdrop.classList.add('active'); } }

window.addEventListener('beforeunload', () => { if (parkingUpdateInterval) clearInterval(parkingUpdateInterval); });
document.addEventListener('DOMContentLoaded', initDashboard);