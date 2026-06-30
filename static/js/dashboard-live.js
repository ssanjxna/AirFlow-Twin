// ============================================================================
// LIVE DASHBOARD OVERRIDES
// ============================================================================

let dashboardLiveFlights = [];
let dashboardLiveParking = null;
let dashboardLiveEvents = [];

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('hotspots-container')) {
        initDashboardLive();
    }
});

async function initDashboardLive() {
    bindDashboardTimeButtons();
    syncDashboardTimeButtons();
    await loadDashboardLiveData();
    setInterval(loadDashboardLiveData, 30000);
}

async function loadDashboardLiveData() {
    try {
        const [flightsResponse, parkingResponse] = await Promise.all([
            fetch('/api/flights'),
            fetch('/api/parking_status'),
        ]);
        const flightsData = await flightsResponse.json();
        dashboardLiveParking = await parkingResponse.json();
        applyHeaderSummary(flightsData.summary);

        const allFlights = [...(flightsData.flights || [])].sort((a, b) => b.risk - a.risk);
        dashboardLiveFlights = allFlights.slice(0, 5);
        dashboardLiveEvents = buildHorizonEvents(allFlights, dashboardLiveParking);
        rememberHorizonEvents(dashboardLiveEvents);

        renderDashboardLiveHotspots(dashboardLiveFlights);
        renderDashboardLiveFlightSummary(allFlights.slice(0, 6));
        renderDashboardLiveEvents(dashboardLiveEvents);
        renderDashboardPredictionMessage(dashboardLiveEvents);
        updateHighRiskCount(allFlights);
    } catch (error) {
        console.error('Error loading live dashboard data:', error);
    }
}

function bindDashboardTimeButtons() {
    document.querySelectorAll('.time-btn').forEach((button) => {
        button.onclick = function () {
            document.querySelectorAll('.time-btn').forEach((btn) => {
                btn.classList.remove('bg-blue-600', 'text-white');
                btn.classList.add('bg-slate-800', 'text-slate-400');
            });

            this.classList.remove('bg-slate-800', 'text-slate-400');
            this.classList.add('bg-blue-600', 'text-white');
            setCurrentTimeStep(parseInt(this.dataset.time, 10));
            renderDashboardLiveEvents(dashboardLiveEvents);
            renderDashboardPredictionMessage(dashboardLiveEvents);
        };
    });
}

function syncDashboardTimeButtons() {
    document.querySelectorAll('.time-btn').forEach((button) => {
        const buttonMinutes = parseInt(button.dataset.time, 10);
        button.classList.remove('bg-blue-600', 'text-white');
        button.classList.add('bg-slate-800', 'text-slate-400');
        if (buttonMinutes === currentTimeStep) {
            button.classList.remove('bg-slate-800', 'text-slate-400');
            button.classList.add('bg-blue-600', 'text-white');
        }
    });
}

function renderDashboardLiveHotspots(flights) {
    const container = document.getElementById('hotspots-container');
    if (!container) return;
    container.innerHTML = '';

    flights.forEach((flight, index) => {
        const pos = resolveHotspotPosition(flight, index, flights.length);
        const hotspot = document.createElement('div');
        hotspot.className = 'hotspot ' + getRiskClass(flight.risk);
        hotspot.style.left = pos.x + '%';
        hotspot.style.top = pos.y + '%';
        hotspot.innerHTML = `<div class="hotspot-marker"></div><div class="hotspot-label"><span class="flight-id">${flight.id}</span><span class="risk-text">${flight.risk}% Risk</span></div>`;
        hotspot.onclick = (event) => {
            event.stopPropagation();
            window.location.href = `/flight/${flight.id}`;
        };
        container.appendChild(hotspot);
    });

    const parkingZone = document.createElement('div');
    parkingZone.className = 'parking-zone';
    parkingZone.style.left = PARKING_ZONE_POSITION.x + '%';
    parkingZone.style.top = PARKING_ZONE_POSITION.y + '%';
    parkingZone.style.width = '250px';
    parkingZone.style.height = '180px';
    parkingZone.innerHTML = '<div class="parking-label">PARKING CONGESTION RISK</div>';
    parkingZone.onclick = (event) => {
        event.stopPropagation();
        window.location.href = '/parking';
    };
    container.appendChild(parkingZone);
}

function renderDashboardLiveFlightSummary(flights) {
    const tbody = document.getElementById('flight-risk-table-summary');
    if (!tbody) return;
    tbody.innerHTML = '';

    flights.forEach((flight) => {
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

function renderDashboardLiveEvents(events) {
    const timeline = document.getElementById('event-timeline-summary');
    if (!timeline) return;
    timeline.innerHTML = '';

    const threshold = currentTimeStep || 15;
    const visibleEvents = events.filter((event) => event.minutesAhead <= threshold);
    const eventsToShow = visibleEvents.length ? visibleEvents : events.slice(0, 3);

    if (!eventsToShow.length) {
        timeline.innerHTML = '<div class="text-xs text-slate-500">No upcoming critical events.</div>';
        return;
    }

    eventsToShow.forEach((event, index) => {
        const item = document.createElement('div');
        item.className = 'text-xs p-3 rounded bg-slate-800/50 border border-slate-700 cursor-pointer hover:bg-slate-800 transition';
        item.innerHTML = `
            <div class="flex justify-between items-start mb-1">
                <span class="text-slate-500 font-semibold">${event.time}</span>
                <span class="px-2 py-0.5 ${getBadgeClass(event.risk)} text-white text-[10px] font-bold rounded">${getPriorityLabel(event.risk)}</span>
            </div>
            <div class="text-slate-300 font-medium">${event.text}</div>
        `;
        item.onclick = () => {
            rememberSelectedHorizonEvent(event);
            window.location.href = `/event/${index}`;
        };
        timeline.appendChild(item);
    });
}

function renderDashboardPredictionMessage(events) {
    const message = document.getElementById('prediction-message');
    if (!message) return;

    if (!events.length) {
        message.textContent = 'Current state: Normal operations.';
        return;
    }

    const highestRisk = Math.max(...events.map((event) => event.risk));
    if (highestRisk >= 80) {
        message.textContent = 'Current state: Elevated operational risk. Active mitigation recommended.';
    } else if (highestRisk >= 50) {
        message.textContent = 'Current state: Watchlist conditions detected in the next horizon.';
    } else {
        message.textContent = 'Current state: Normal operations.';
    }
}
