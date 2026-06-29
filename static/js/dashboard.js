const hotspotPositions = {
    'UK-633': { x: 92, y: 42 },
    'BA-6017': { x: 76, y: 28 },
    'BA-7303': { x: 60, y: 19 },
    'KL-7243': { x: 44, y: 14 },
    'SG-1280': { x: 30, y: 10 },
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
            { time: '+5m', text: 'BA-6017 taxiing to gate', type: 'info' }
        ],
        message: "Minor ground movements expected.",
        modifiers: {
            'BA-6017': { risk: 65, delay: 32 }
        },
        newFlights: []
    },
    30: {
        events: [
            { time: '+15m', text: '️ Maintenance Crew Shift Change', type: 'warning' },
            { time: '+25m', text: '✈️ New Arrival: EK-9988 (A380)', type: 'critical' },
            { time: '+28m', text: 'Parking capacity reaches 85%', type: 'warning' }
        ],
        message: "Risk increasing due to crew shift change and incoming traffic.",
        modifiers: {
            'BA-6017': { risk: 75, delay: 35, reason: 'Congestion from incoming EK-9988' },
            'SG-1280': { risk: 85, delay: 45, reason: 'Shift change delay' }
        },
        newFlights: [
            { id: 'EK-9988', origin: 'DXB', destination: 'LHR', risk: 85, delay: 45, status: 'Approaching', aircraft_type: 'A380' }
        ]
    },
    60: {
        events: [
            { time: '+40m', text: '⛈️ Weather Warning: Heavy rain at DOH', type: 'critical' },
            { time: '+50m', text: 'Ground operations slowed by 40%', type: 'warning' },
            { time: '+55m', text: '3 flights rerouted to alternate gates', type: 'info' }
        ],
        message: "Severe weather impacting incoming flights from Doha.",
        modifiers: {
            'EK-9988': { risk: 92, delay: 60, reason: 'Weather delay + Ground congestion' },
            'SG-1280': { risk: 88, delay: 50, reason: 'Weather compounding existing delay' }
        },
        newFlights: []
    }
};

// Risk forecast data for each flight at each time step
const riskForecasts = {
    'UK-633': [61, 63, 70, 75],
    'BA-6017': [61, 65, 75, 82],
    'BA-7303': [61, 62, 68, 74],
    'KL-7243': [36, 38, 45, 52],
    'SG-1280': [80, 82, 85, 88],
    'EK-9988': [0, 0, 85, 92],
    'PARKING': [60, 65, 75, 85]
};

// Recommendations database
const recommendationsDB = {
    'SG-1280': [
        { id: 'rec1', text: 'Reassign maintenance crew from KL-7243 (lower priority)', impact: '-15m delay, -20% risk', riskReduction: 20, delayReduction: 15 },
        { id: 'rec2', text: 'Open Overflow Parking P3 for passenger traffic', impact: '-8m delay, -10% risk', riskReduction: 10, delayReduction: 8 },
        { id: 'rec3', text: 'Activate dynamic signage to route traffic', impact: '-5m delay, -5% risk', riskReduction: 5, delayReduction: 5 },
        { id: 'rec4', text: 'Pre-position fuel truck at Gate A12', impact: '-3m delay, -3% risk', riskReduction: 3, delayReduction: 3 }
    ],
    'EK-9988': [
        { id: 'rec1', text: 'Pre-assign Crew B before shift change completes', impact: '-20m delay, -25% risk', riskReduction: 25, delayReduction: 20 },
        { id: 'rec2', text: 'Route to Gate A4 (closest to active crew)', impact: '-12m delay, -15% risk', riskReduction: 15, delayReduction: 12 },
        { id: 'rec3', text: 'Priority baggage handling team allocation', impact: '-8m delay, -10% risk', riskReduction: 10, delayReduction: 8 }
    ],
    'default': [
        { id: 'rec1', text: 'Reassign maintenance crew to this flight', impact: '-12m delay, -15% risk', riskReduction: 15, delayReduction: 12 },
        { id: 'rec2', text: 'Open overflow parking for passenger traffic', impact: '-8m delay, -10% risk', riskReduction: 10, delayReduction: 8 },
        { id: 'rec3', text: 'Activate dynamic traffic signage', impact: '-5m delay, -5% risk', riskReduction: 5, delayReduction: 5 }
    ]
};

let selectedFlightId = null;
let currentTimeStep = 0;
let selectedRecommendations = new Set();

async function initDashboard() {
    await loadAndRenderData();
    setupTimeControls();
    setupMapScroll();
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
}

async function loadAndRenderData() {
    try {
        const response = await fetch('/api/flights');
        const baseData = await response.json();
        let flights = baseData.flights.filter(f => hotspotPositions[f.id]).slice(0, 5);
        
        const scenario = futureScenarios[currentTimeStep];
        
        if (scenario.modifiers) {
            flights = flights.map(f => {
                if (scenario.modifiers[f.id]) {
                    return { ...f, ...scenario.modifiers[f.id] };
                }
                return f;
            });
        }
        
        if (scenario.newFlights) {
            scenario.newFlights.forEach(newF => {
                if (!flights.find(f => f.id === newF.id)) {
                    flights.push(newF);
                }
            });
        }

        updateEventTimeline(scenario);
        updateRiskForecast();
        renderHotspots(flights);
        renderFlightRiskTable(flights);
        updateHighRiskCount(flights);
        
        if (currentTimeStep > 0 && !selectedFlightId) {
            const highestRisk = [...flights].sort((a, b) => b.risk - a.risk)[0];
            if (highestRisk && highestRisk.risk > 70) {
                selectFlight(highestRisk);
            }
        }

    } catch (error) {
        console.error('Error loading data:', error);
    }
}

function updateEventTimeline(scenario) {
    const timeline = document.getElementById('event-timeline');
    if (!timeline) {
        console.error('Event timeline element not found');
        return;
    }
    
    timeline.innerHTML = '';
    
    if (!scenario.events || scenario.events.length === 0) {
        timeline.innerHTML = `
            <div class="event-item info">
                <span class="event-time">--</span>
                <span class="event-text">No events scheduled in the next hour.</span>
            </div>
        `;
    } else {
        scenario.events.forEach(evt => {
            const div = document.createElement('div');
            div.className = `event-item ${evt.type || 'info'}`;
            div.innerHTML = `
                <span class="event-time">${evt.time || '--'}</span>
                <span class="event-text">${evt.text || 'Event'}</span>
            `;
            timeline.appendChild(div);
        });
    }
    
    const msgDiv = document.getElementById('prediction-message');
    if (msgDiv) {
        msgDiv.textContent = scenario.message || 'Viewing current state.';
    }
}

function updateRiskForecast() {
    const flightId = selectedFlightId || 'SG-1280';
    const forecast = riskForecasts[flightId] || [60, 65, 75, 85];
    
    // Update bar heights with minimum height
    const bars = [
        { id: 'bar-now', value: forecast[0] },
        { id: 'bar-10', value: forecast[1] },
        { id: 'bar-30', value: forecast[2] },
        { id: 'bar-60', value: forecast[3] }
    ];
    
    bars.forEach(bar => {
        const element = document.getElementById(bar.id);
        if (element) {
            // Set height as percentage but ensure minimum visibility
            const height = Math.max(bar.value, 10); // Minimum 10% height
            element.style.height = height + '%';
            
            // Update color based on risk level
            if (bar.value > 70) {
                element.className = 'w-full bg-red-500 rounded-t transition-all duration-500 relative group';
            } else if (bar.value > 40) {
                element.className = 'w-full bg-orange-500 rounded-t transition-all duration-500 relative group';
            } else {
                element.className = 'w-full bg-green-500 rounded-t transition-all duration-500 relative group';
            }
            
            // Update tooltip
            const tooltip = document.getElementById(bar.id.replace('bar', 'tooltip'));
            if (tooltip) {
                tooltip.textContent = bar.value + '%';
            }
        }
    });
    
    // Update labels
    const labels = [
        { id: 'risk-now-label', value: forecast[0] },
        { id: 'risk-10-label', value: forecast[1] },
        { id: 'risk-30-label', value: forecast[2] },
        { id: 'risk-60-label', value: forecast[3] }
    ];
    
    labels.forEach(label => {
        const element = document.getElementById(label.id);
        if (element) {
            element.textContent = label.value + '%';
        }
    });
}

function renderHotspots(flights) {
    const container = document.getElementById('hotspots-container');
    container.innerHTML = '';

    flights.forEach(flight => {
        if (!hotspotPositions[flight.id]) return;

        const pos = hotspotPositions[flight.id];
        let riskClass = 'low-risk';
        if (flight.risk > 70) riskClass = 'high-risk';
        else if (flight.risk > 40) riskClass = 'medium-risk';

        const hotspot = document.createElement('div');
        hotspot.className = 'hotspot ' + riskClass;
        hotspot.style.left = pos.x + '%';
        hotspot.style.top = pos.y + '%';
        
        if (currentTimeStep === 30 && flight.id === 'EK-9988') {
            hotspot.style.animation = 'pulse-red 1s infinite';
        }

        const marker = document.createElement('div');
        marker.className = 'hotspot-marker';
        hotspot.appendChild(marker);
        
        const label = document.createElement('div');
        label.className = 'hotspot-label';
        label.innerHTML = `<span class="flight-id">${flight.id}</span> <span class="risk-text">${flight.risk}%</span>`;
        hotspot.appendChild(label);

        hotspot.onclick = (e) => {
            e.stopPropagation();
            selectFlight(flight);
        };
        container.appendChild(hotspot);
    });

    const parkingPos = hotspotPositions['PARKING'];
    if (parkingPos) {
        const zone = document.createElement('div');
        zone.className = 'congestion-zone';
        zone.style.left = parkingPos.x + '%';
        zone.style.top = parkingPos.y + '%';
        zone.style.width = '120px';
        zone.style.height = '80px';
        zone.innerHTML = '<div class="congestion-label">PARKING CONGESTION</div>';
        zone.onclick = (e) => {
            e.stopPropagation();
            selectFlight({ id: 'PARKING', risk: 60, origin: 'Landside', destination: 'Terminal', delay_minutes: 15 });
        };
        container.appendChild(zone);
    }
}

function renderFlightRiskTable(flights) {
    const tbody = document.getElementById('flight-risk-table');
    tbody.innerHTML = '';

    const sortedFlights = [...flights].sort((a, b) => b.risk - a.risk);

    sortedFlights.forEach((flight) => {
        let riskColor = flight.risk > 70 ? 'text-red-500' : (flight.risk > 40 ? 'text-orange-500' : 'text-green-500');
        let riskBg = flight.risk > 70 ? 'bg-red-500' : (flight.risk > 40 ? 'bg-orange-500' : 'bg-green-500');
        let delay = flight.delay_minutes || Math.floor(flight.risk * 0.5);
        
        let priority = flight.risk > 70 ? 'CRITICAL' : (flight.risk > 40 ? 'HIGH' : 'NORMAL');
        let priorityClass = flight.risk > 70 ? 'bg-red-500/20 text-red-400 border-red-500/30' : (flight.risk > 40 ? 'bg-orange-500/20 text-orange-400 border-orange-500/30' : 'bg-green-500/20 text-green-400 border-green-500/30');

        const row = document.createElement('tr');
        row.className = 'flight-row border-b border-slate-800 hover:bg-slate-800/50 transition cursor-pointer';
        if (selectedFlightId === flight.id) row.classList.add('bg-slate-800/70');
        
        row.innerHTML = `
            <td class="py-2">
                <div class="flex items-center gap-2">
                    <span class="text-[9px] font-bold px-1.5 py-0.5 rounded border ${priorityClass}">${priority}</span>
                    <span class="font-bold text-white text-xs">${flight.id}</span>
                </div>
            </td>
            <td class="py-2 text-slate-400 text-xs">${flight.origin} → ${flight.destination}</td>
            <td class="py-2 text-right ${riskColor} font-medium text-xs">${delay}m</td>
            <td class="py-2 text-right">
                <div class="flex items-center justify-end gap-2">
                    <div class="w-12 h-1 bg-slate-700 rounded-full overflow-hidden">
                        <div class="h-full ${riskBg} rounded-full" style="width: ${flight.risk}%"></div>
                    </div>
                    <span class="font-bold ${riskColor} text-xs w-8 text-right">${flight.risk}%</span>
                </div>
            </td>
        `;
        row.onclick = () => selectFlight(flight);
        tbody.appendChild(row);
    });
}

async function selectFlight(flight) {
    selectedFlightId = flight.id;
    selectedRecommendations.clear();
    
    document.getElementById('default-state').classList.add('hidden');
    document.getElementById('selected-flight-card').classList.remove('hidden');
    document.getElementById('selected-flight-card').classList.add('flex');
    
    document.getElementById('selected-flight-id').textContent = flight.id;
    document.getElementById('selected-flight-route').textContent = `${flight.origin} → ${flight.destination}`;
    
    let riskColor = flight.risk > 70 ? 'text-red-500' : (flight.risk > 40 ? 'text-orange-500' : 'text-green-500');
    let badgeClass = flight.risk > 70 ? 'bg-red-600' : (flight.risk > 40 ? 'bg-orange-600' : 'bg-green-600');
    let riskText = flight.risk > 70 ? 'HIGH RISK' : (flight.risk > 40 ? 'MEDIUM RISK' : 'LOW RISK');
    
    const badge = document.getElementById('risk-badge');
    badge.textContent = riskText;
    badge.className = `px-2 py-1 ${badgeClass} text-white text-[10px] font-bold rounded`;
    
    document.getElementById('risk-score-value').textContent = flight.risk;
    document.getElementById('risk-score-value').className = `text-lg font-bold ${riskColor}`;
    document.getElementById('predicted-delay').textContent = (flight.delay_minutes || Math.floor(flight.risk * 0.5)) + 'm';
    document.getElementById('confidence').textContent = Math.floor(80 + Math.random() * 15) + '%';
    
    let causeText = "Aircraft maintenance delay and high predicted passenger arrival time due to landside traffic.";
    if (currentTimeStep === 30 && flight.id === 'EK-9988') {
        causeText = "New arrival overlapping with Maintenance Crew Shift Change. No ground crew available for immediate turnaround.";
    } else if (flight.risk > 70 && currentTimeStep === 60) {
        causeText = "Severe weather delay at origin compounded by current ground congestion.";
    }
    document.getElementById('risk-cause').textContent = causeText;

    renderRecommendationCards(flight);
    updateExpectedImpact();
    updateRiskForecast();
    updateApplyButton();

    await loadAndRenderData(); 
}

function renderRecommendationCards(flight) {
    const container = document.getElementById('ai-recommendations');
    container.innerHTML = '';
    
    const recs = recommendationsDB[flight.id] || recommendationsDB['default'];
    
    recs.forEach(rec => {
        const card = document.createElement('div');
        card.className = 'rec-card';
        card.dataset.recId = rec.id;
        card.onclick = () => toggleRecommendation(rec.id, card);
        
        card.innerHTML = `
            <div class="rec-checkbox">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>
            </div>
            <div class="rec-content">
                <div class="rec-text">${rec.text}</div>
                <div class="rec-impact">${rec.impact}</div>
            </div>
        `;
        
        container.appendChild(card);
    });
}

function toggleRecommendation(recId, cardElement) {
    if (selectedRecommendations.has(recId)) {
        selectedRecommendations.delete(recId);
        cardElement.classList.remove('selected');
    } else {
        selectedRecommendations.add(recId);
        cardElement.classList.add('selected');
    }
    updateExpectedImpact();
    updateApplyButton();
}

function selectAllRecommendations() {
    const cards = document.querySelectorAll('.rec-card');
    cards.forEach(card => {
        const recId = card.dataset.recId;
        selectedRecommendations.add(recId);
        card.classList.add('selected');
    });
    updateExpectedImpact();
    updateApplyButton();
}

function updateExpectedImpact() {
    const flightId = selectedFlightId;
    const recs = recommendationsDB[flightId] || recommendationsDB['default'];
    
    let totalRiskReduction = 0;
    let totalDelayReduction = 0;
    
    selectedRecommendations.forEach(recId => {
        const rec = recs.find(r => r.id === recId);
        if (rec) {
            totalRiskReduction += rec.riskReduction;
            totalDelayReduction += rec.delayReduction;
        }
    });
    
    const currentRisk = parseInt(document.getElementById('risk-score-value').textContent) || 80;
    const currentDelay = parseInt(document.getElementById('predicted-delay').textContent) || 40;
    
    const newRisk = Math.max(10, currentRisk - totalRiskReduction);
    const newDelay = Math.max(0, currentDelay - totalDelayReduction);
    
    document.getElementById('expected-risk-after').textContent = newRisk + '%';
    document.getElementById('expected-delay-reduction').textContent = totalDelayReduction + 'm';
}

function updateApplyButton() {
    const btn = document.getElementById('apply-btn');
    if (selectedRecommendations.size === 0) {
        btn.disabled = true;
        btn.textContent = 'Select at least one recommendation';
    } else {
        btn.disabled = false;
        btn.textContent = `Apply ${selectedRecommendations.size} Recommendation${selectedRecommendations.size > 1 ? 's' : ''}`;
    }
}

async function applySelectedRecommendations() {
    const btn = document.getElementById('apply-btn');
    btn.textContent = 'Applying...';
    btn.disabled = true;
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const flightId = selectedFlightId;
    const recs = recommendationsDB[flightId] || recommendationsDB['default'];
    
    let totalRiskReduction = 0;
    let totalDelayReduction = 0;
    
    selectedRecommendations.forEach(recId => {
        const rec = recs.find(r => r.id === recId);
        if (rec) {
            totalRiskReduction += rec.riskReduction;
            totalDelayReduction += rec.delayReduction;
        }
    });
    
    const currentRisk = parseInt(document.getElementById('risk-score-value').textContent) || 80;
    const newRisk = Math.max(10, currentRisk - totalRiskReduction);
    
    document.getElementById('risk-score-value').textContent = newRisk;
    document.getElementById('risk-score-value').className = `text-lg font-bold ${newRisk > 70 ? 'text-red-500' : (newRisk > 40 ? 'text-orange-500' : 'text-green-500')}`;
    
    const currentDelay = parseInt(document.getElementById('predicted-delay').textContent) || 40;
    const newDelay = Math.max(0, currentDelay - totalDelayReduction);
    document.getElementById('predicted-delay').textContent = newDelay + 'm';
    
    renderHotspots([{ id: flightId, risk: newRisk, origin: 'DEL', destination: 'KUL' }]);
    
    await loadAndRenderData();
    
    btn.textContent = '✓ Applied Successfully!';
    btn.classList.add('success');
    
    setTimeout(() => {
        btn.textContent = 'Select at least one recommendation';
        btn.classList.remove('success');
        btn.disabled = false;
        selectedRecommendations.clear();
        document.querySelectorAll('.rec-card').forEach(card => card.classList.remove('selected'));
        updateApplyButton();
    }, 2000);
}

function setupTimeControls() {
    const buttons = document.querySelectorAll('.time-btn');
    const slider = document.querySelector('.slider');
    
    buttons.forEach(btn => {
        btn.onclick = function() {
            buttons.forEach(b => {
                b.classList.remove('bg-blue-600', 'text-white');
                b.classList.add('bg-slate-800', 'text-slate-400');
            });
            this.classList.remove('bg-slate-800', 'text-slate-400');
            this.classList.add('bg-blue-600', 'text-white');
            
            currentTimeStep = parseInt(this.dataset.time);
            slider.value = currentTimeStep;
            
            loadAndRenderData();
        };
    });

    slider.oninput = function() {
        const val = parseInt(this.value);
        const snapped = Math.round(val / 10) * 10;
        this.value = snapped;
        
        const targetBtn = document.querySelector(`.time-btn[data-time="${snapped}"]`);
        if (targetBtn) targetBtn.click();
    };
}

function setupMapScroll() {
    const scrollContainer = document.getElementById('map-scroll-container');
}

function updateCurrentTime() {
    document.getElementById('current-time').textContent = new Date().toTimeString().split(' ')[0];
}

function updateHighRiskCount(flights) {
    document.getElementById('high-risk-count').textContent = flights.filter(f => f.risk > 70).length;
}

document.addEventListener('DOMContentLoaded', initDashboard);