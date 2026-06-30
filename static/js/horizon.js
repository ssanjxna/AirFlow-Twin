// ============================================================================
// PREDICTION HORIZON PAGE LOGIC (horizon.html)
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('horizon-event-timeline')) {
        initHorizonPage();
    }
});

async function initHorizonPage() {
    renderHorizonTimeline();
    setupTimeControls();
}

function renderHorizonTimeline() {
    const timeline = document.getElementById('horizon-event-timeline');
    const eventCount = document.getElementById('event-count');
    
    if (!timeline) return;
    
    const scenario = futureScenarios[currentTimeStep];
    const eventsToShow = scenario.events;
    
    eventCount.textContent = `${eventsToShow.length} event${eventsToShow.length !== 1 ? 's' : ''}`;
    
    if (eventsToShow.length === 0) {
        timeline.innerHTML = `
            <div class="bg-slate-800/50 rounded-lg p-6 text-center border border-slate-700">
                <svg class="w-12 h-12 text-slate-600 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p class="text-sm text-slate-400">No upcoming events in this time horizon.</p>
            </div>
        `;
    } else {
        timeline.innerHTML = '';
        eventsToShow.forEach((evt, index) => {
            const div = document.createElement('div');
            let itemClass = evt.risk >= 80 ? 'critical' : (evt.risk >= 50 ? 'warning' : 'info');
            
            div.className = `event-item ${itemClass} p-4 rounded-lg border cursor-pointer hover:bg-slate-800/70 transition`;
            div.innerHTML = `
                <div class="flex justify-between items-start mb-2">
                    <div class="flex-1">
                        <span class="text-xs text-slate-500 font-semibold">${evt.time}</span>
                        <h4 class="text-sm font-bold text-white mt-1">${evt.text}</h4>
                    </div>
                    <span class="px-2 py-1 ${getBadgeClass(evt.risk)} text-white text-xs font-bold rounded uppercase">
                        ${getPriorityLabel(evt.risk)}
                    </span>
                </div>
                <p class="text-xs text-slate-400 mb-3">${evt.impact}</p>
                <div class="flex justify-between items-center">
                    <span class="text-xs ${getRiskColor(evt.risk)} font-bold">${evt.risk}% Risk</span>
                    <button onclick="window.location.href='/event/${index}'" class="text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded transition">
                        View AI Analysis →
                    </button>
                </div>
            `;
            timeline.appendChild(div);
        });
    }
}

function setupTimeControls() {
    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.onclick = function() {
            document.querySelectorAll('.time-btn').forEach(b => { 
                b.classList.remove('bg-blue-600', 'text-white'); 
                b.classList.add('bg-slate-800', 'text-slate-400'); 
            });
            this.classList.remove('bg-slate-800', 'text-slate-400');
            this.classList.add('bg-blue-600', 'text-white');
            currentTimeStep = parseInt(this.dataset.time);
            renderHorizonTimeline();
        };
    });
}