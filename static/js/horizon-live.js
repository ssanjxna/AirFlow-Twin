// ============================================================================
// LIVE HORIZON PAGE OVERRIDES
// ============================================================================

let horizonLiveFlights = [];
let horizonLiveParking = null;
let horizonLiveEvents = [];

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('horizon-event-timeline')) {
        initHorizonLivePage();
    }
});

async function initHorizonLivePage() {
    bindHorizonTimeButtons();
    syncHorizonTimeButtons();
    await loadHorizonLiveData();
}

async function loadHorizonLiveData() {
    try {
        const [flightsData, parkingData] = await Promise.all([
            fetchLiveJson('/api/flights?limit=24'),
            fetchLiveJson('/api/parking_status'),
        ]);
        horizonLiveFlights = flightsData.flights || [];
        horizonLiveParking = parkingData;
        horizonLiveEvents = buildHorizonEvents(horizonLiveFlights, horizonLiveParking);
        rememberHorizonEvents(horizonLiveEvents);
        applyHeaderSummary(flightsData.summary);

        renderHorizonLiveBars();
        renderHorizonLiveTimeline();
    } catch (error) {
        console.error('Error loading horizon data:', error);
    }
}

function bindHorizonTimeButtons() {
    document.querySelectorAll('.time-btn').forEach((button) => {
        button.onclick = function () {
            document.querySelectorAll('.time-btn').forEach((btn) => {
                btn.classList.remove('bg-blue-600', 'text-white');
                btn.classList.add('bg-slate-800', 'text-slate-400');
            });

            this.classList.remove('bg-slate-800', 'text-slate-400');
            this.classList.add('bg-blue-600', 'text-white');
            setCurrentTimeStep(parseInt(this.dataset.time, 10));
            renderHorizonLiveTimeline();
        };
    });
}

function syncHorizonTimeButtons() {
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

function renderHorizonLiveBars() {
    const topFlights = [...horizonLiveFlights].sort((a, b) => b.risk - a.risk).slice(0, 5);
    const baseRisk = topFlights.length
        ? Math.round(topFlights.reduce((sum, flight) => sum + flight.risk, 0) / topFlights.length)
        : 0;
    const risk10 = Math.max(baseRisk, Math.round(horizonLiveEvents.filter((event) => event.minutesAhead <= 15).reduce((max, event) => Math.max(max, event.risk), baseRisk)));
    const risk30 = Math.max(risk10, Math.round(horizonLiveEvents.filter((event) => event.minutesAhead <= 30).reduce((max, event) => Math.max(max, event.risk), risk10)));
    const risk60 = Math.max(risk30, Math.round(horizonLiveEvents.reduce((max, event) => Math.max(max, event.risk), risk30)));

    const levels = [
        { id: 'now', risk: baseRisk || 25 },
        { id: '10', risk: risk10 || 30 },
        { id: '30', risk: risk30 || 35 },
        { id: '60', risk: risk60 || 40 },
    ];

    levels.forEach((level) => {
        const bar = document.getElementById(`bar-${level.id}`);
        const label = document.getElementById(`risk-${level.id}-label`);
        if (bar) bar.style.height = `${clampValue(level.risk, 10, 100)}%`;
        if (label) label.textContent = `${level.risk}%`;
    });
}

function renderHorizonLiveTimeline() {
    const timeline = document.getElementById('horizon-event-timeline');
    const eventCount = document.getElementById('event-count');
    const predictionMessage = document.getElementById('prediction-message');
    if (!timeline) return;

    const threshold = currentTimeStep || 60;
    const visibleEvents = horizonLiveEvents.filter((event) => event.minutesAhead <= threshold);
    eventCount.textContent = `${visibleEvents.length} event${visibleEvents.length !== 1 ? 's' : ''}`;
    timeline.innerHTML = '';

    if (!visibleEvents.length) {
        timeline.innerHTML = `
            <div class="bg-slate-800/50 rounded-lg p-6 text-center border border-slate-700">
                <p class="text-sm text-slate-400">No upcoming events in this time horizon.</p>
            </div>
        `;
        if (predictionMessage) predictionMessage.textContent = 'Current state: Normal operations.';
        return;
    }

    visibleEvents.forEach((event, index) => {
        const item = document.createElement('div');
        const itemClass = event.risk >= 80 ? 'critical' : (event.risk >= 50 ? 'warning' : 'info');
        item.className = `event-item ${itemClass} p-4 rounded-lg border cursor-pointer hover:bg-slate-800/70 transition`;
        item.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <div class="flex-1">
                    <span class="text-xs text-slate-500 font-semibold">${event.time}</span>
                    <h4 class="text-sm font-bold text-white mt-1">${event.text}</h4>
                </div>
                <span class="px-2 py-1 ${getBadgeClass(event.risk)} text-white text-xs font-bold rounded uppercase">
                    ${getPriorityLabel(event.risk)}
                </span>
            </div>
            <p class="text-xs text-slate-400 mb-3">${event.impact}</p>
            <div class="flex justify-between items-center">
                <span class="text-xs ${getRiskColor(event.risk)} font-bold">${event.risk}% Risk</span>
                <button class="text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded transition">
                    View AI Analysis →
                </button>
            </div>
        `;
        item.onclick = () => {
            rememberSelectedHorizonEvent(event);
            window.location.href = `/event/${index}`;
        };
        timeline.appendChild(item);
    });

    if (predictionMessage) {
        const highestRisk = Math.max(...visibleEvents.map((event) => event.risk));
        predictionMessage.textContent = highestRisk >= 80
            ? 'Current state: Elevated operational risk. Mitigation actions recommended.'
            : 'Current state: Watchlist conditions detected in the selected horizon.';
    }
}
