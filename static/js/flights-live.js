// ============================================================================
// LIVE FLIGHTS PAGE OVERRIDES
// ============================================================================

let liveFlightsPageData = [];

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('all-flights-table-body')) {
        initFlightsLivePage();
    }
});

async function initFlightsLivePage() {
    try {
        const response = await fetch('/api/flights');
        const data = await response.json();
        liveFlightsPageData = data.flights || [];
        applyHeaderSummary(data.summary);
        renderLiveFlightsTable(liveFlightsPageData);
    } catch (error) {
        console.error('Error loading live flights:', error);
    }
}

function renderLiveFlightsTable(flights) {
    const tbody = document.getElementById('all-flights-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    [...flights]
        .sort((a, b) => b.risk - a.risk)
        .forEach((flight) => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-800/50 transition cursor-pointer';
            tr.onclick = () => { window.location.href = `/flight/${flight.id}`; };
            tr.innerHTML = `
                <td class="px-6 py-4 font-bold text-white flex items-center gap-3">
                    <span class="px-2 py-1 rounded border text-[10px] ${getPriorityClass(flight.risk)}">${getPriorityLabel(flight.risk)}</span>
                    ${flight.id}
                </td>
                <td class="px-6 py-4 text-slate-400">${flight.origin} → ${flight.destination}</td>
                <td class="px-6 py-4 text-slate-400">${flight.aircraft_type || 'A320'}</td>
                <td class="px-6 py-4"><span class="px-2 py-1 rounded bg-slate-800 text-xs text-slate-300">${flight.status || 'Scheduled'}</span></td>
                <td class="px-6 py-4 text-right font-bold ${getRiskColor(flight.risk)}">${flight.predicted_delay_minutes}m</td>
                <td class="px-6 py-4 text-right">
                    <div class="flex items-center justify-end gap-2">
                        <div class="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                            <div class="h-full ${getRiskBg(flight.risk)} rounded-full" style="width: ${flight.risk}%"></div>
                        </div>
                        <span class="font-bold ${getRiskColor(flight.risk)} w-8 text-right">${flight.risk}%</span>
                    </div>
                </td>
                <td class="px-6 py-4 text-center">
                    <button class="text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded transition">Analyze →</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
}

function sortTable(criteria) {
    if (criteria === 'risk') {
        liveFlightsPageData.sort((a, b) => b.risk - a.risk);
    } else if (criteria === 'delay') {
        liveFlightsPageData.sort((a, b) => (b.predicted_delay_minutes || 0) - (a.predicted_delay_minutes || 0));
    }
    renderLiveFlightsTable(liveFlightsPageData);
}
