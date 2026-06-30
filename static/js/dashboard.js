// ============================================================================
// MAIN DASHBOARD LOGIC (index.html)
// ============================================================================

let currentFlights = [];
let currentParkingData = null;

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('hotspots-container')) {
        initMainDashboard();
    }
});

async function initMainDashboard() {
    await loadAndRenderData();
    await updateParkingStatus();
    setInterval(updateCurrentTime, 1000);
    setInterval(updateParkingStatus, 30000);
}

async function loadAndRenderData() {
    try {
        const response = await fetch('/api/flights');
        const baseData = await response.json();
        let flights = baseData.flights.filter(f => hotspotPositions[f.id]).slice(0, 5);
        
        const scenario = futureScenarios[0];
        if (scenario.modifiers) {
            flights = flights.map(f => scenario.modifiers[f.id] ? { ...f, ...scenario.modifiers[f.id] } : f);
        }
        if (scenario.newFlights) {
            scenario.newFlights.forEach(newF => { 
                if (!flights.find(f => f.id === newF.id)) flights.push(newF); 
            });
        }
        
        currentFlights = flights;
        renderHotspots(flights);
        renderFlightRiskTableSummary(flights);
        updateEventTimelineSummary(scenario);
        updateHighRiskCount(flights);
    } catch (error) { 
        console.error('Error loading data:', error); 
    }
}

function renderHotspots(flights) {
    const container = document.getElementById('hotspots-container');
    if (!container) return;
    container.innerHTML = '';

    flights.forEach(flight => {
        if (!hotspotPositions[flight.id]) return;
        const pos = hotspotPositions[flight.id];
        const hotspot = document.createElement('div');
        hotspot.className = 'hotspot ' + getRiskClass(flight.risk);
        hotspot.style.left = pos.x + '%';
        hotspot.style.top = pos.y + '%';
        hotspot.innerHTML = `<div class="hotspot-marker"></div><div class="hotspot-label"><span class="flight-id">${flight.id}</span><span class="risk-text">${flight.risk}% Risk</span></div>`;
        
        hotspot.onclick = (e) => { 
            e.stopPropagation(); 
            window.location.href = `/flight/${flight.id}`; 
        };
        container.appendChild(hotspot);
    });

    const parkingPos = hotspotPositions['PARKING'];
    if (parkingPos) {
        const zone = document.createElement('div');
        zone.className = 'parking-zone';
        zone.style.left = parkingPos.x + '%';
        zone.style.top = parkingPos.y + '%';
        zone.style.width = '250px';
        zone.style.height = '180px';
        zone.innerHTML = `<div class="parking-label">🚨 PARKING CONGESTION RISK</div>`;
        
        zone.onclick = (e) => { 
            e.stopPropagation(); 
            window.location.href = '/parking'; 
        };
        container.appendChild(zone);
    }
}

function renderFlightRiskTableSummary(flights) {
    const tbody = document.getElementById('flight-risk-table-summary');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    const sortedFlights = [...flights].sort((a, b) => b.risk - a.risk);
    sortedFlights.forEach((flight) => {
        const row = document.createElement('tr');
        row.className = 'flight-row border-b border-slate-800 hover:bg-slate-800/50 transition cursor-pointer';
        row.innerHTML = `
            <td class="py-2"><span class="font-bold text-white">${flight.id}</span></td>
            <td class="py-2 text-right"><span class="font-bold ${getRiskColor(flight.risk)}">${flight.risk}%</span></td>
        `;
        row.onclick = () => { window.location.href = `/flight/${flight.id}`; };
        tbody.appendChild(row);
    });
}

function updateEventTimelineSummary(scenario) {
    const timeline = document.getElementById('event-timeline-summary');
    if (!timeline) return;
    timeline.innerHTML = '';
    
    const eventsToShow = scenario.events.filter(evt => evt.risk >= 50);
    if (eventsToShow.length === 0) {
        timeline.innerHTML = `<div class="text-xs text-slate-500">No upcoming critical events.</div>`;
    } else {
        eventsToShow.forEach((evt) => {
            const div = document.createElement('div');
            div.className = 'text-xs p-3 rounded bg-slate-800/50 border border-slate-700 cursor-pointer hover:bg-slate-800 transition';
            div.innerHTML = `
                <div class="flex justify-between items-start mb-1">
                    <span class="text-slate-500 font-semibold">${evt.time}</span>
                    <span class="px-2 py-0.5 ${getBadgeClass(evt.risk)} text-white text-[10px] font-bold rounded">${getPriorityLabel(evt.risk)}</span>
                </div>
                <div class="text-slate-300 font-medium">${evt.text}</div>
            `;
            div.onclick = () => { window.location.href = '/horizon'; };
            timeline.appendChild(div);
        });
    }
}

async function updateParkingStatus() {
    try {
        const response = await fetch('/api/parking_status');
        currentParkingData = await response.json();
    } catch (error) { 
        console.error('Error fetching parking status:', error); 
    }
}