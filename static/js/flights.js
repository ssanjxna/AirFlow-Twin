// ============================================================================
// ALL FLIGHTS PAGE LOGIC (flights.html)
// ============================================================================

let allFlightsData = [];

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('all-flights-table-body')) {
        initAllFlightsPage();
    }
});

async function initAllFlightsPage() {
    try {
        const response = await fetch('/api/flights');
        const data = await response.json();
        allFlightsData = data.flights;
        renderAllFlightsTable(allFlightsData);
    } catch (error) {
        console.error('Error loading flights:', error);
    }
}

function renderAllFlightsTable(flights) {
    const tbody = document.getElementById('all-flights-table-body');
    tbody.innerHTML = '';
    
    flights.sort((a, b) => b.risk - a.risk);
    
    flights.forEach(flight => {
        const riskColor = getRiskColor(flight.risk);
        const priorityClass = getPriorityClass(flight.risk);
        const delay = flight.delay_minutes || Math.floor(flight.risk * 0.5);
        
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-800/50 transition cursor-pointer';
        tr.onclick = () => { window.location.href = `/flight/${flight.id}`; };
        
        tr.innerHTML = `
            <td class="px-6 py-4 font-bold text-white flex items-center gap-3">
                <span class="px-2 py-1 rounded border text-[10px] ${priorityClass}">${getPriorityLabel(flight.risk)}</span>
                ${flight.id}
            </td>
            <td class="px-6 py-4 text-slate-400">${flight.origin} → ${flight.destination}</td>
            <td class="px-6 py-4 text-slate-400">${flight.aircraft_type || 'A320'}</td>
            <td class="px-6 py-4"><span class="px-2 py-1 rounded bg-slate-800 text-xs text-slate-300">${flight.status || 'On Ground'}</span></td>
            <td class="px-6 py-4 text-right font-bold ${riskColor}">${delay}m</td>
            <td class="px-6 py-4 text-right">
                <div class="flex items-center justify-end gap-2">
                    <div class="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                        <div class="h-full ${getRiskBg(flight.risk)} rounded-full" style="width: ${flight.risk}%"></div>
                    </div>
                    <span class="font-bold ${riskColor} w-8 text-right">${flight.risk}%</span>
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
        allFlightsData.sort((a, b) => b.risk - a.risk);
    } else if (criteria === 'delay') {
        allFlightsData.sort((a, b) => (b.delay_minutes || 0) - (a.delay_minutes || 0));
    }
    renderAllFlightsTable(allFlightsData);
}