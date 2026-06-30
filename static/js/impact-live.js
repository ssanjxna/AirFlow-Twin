// ============================================================================
// LIVE IMPACT METRICS
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('impact-before-delayed') || document.getElementById('horizon-before-delayed')) {
        loadImpactLiveMetrics();
    }
});

async function loadImpactLiveMetrics() {
    try {
        const response = await fetch('/api/flights?limit=24');
        const data = await response.json();
        const flights = data.flights || [];
        const summary = data.summary || {};

        const beforeDelayed = flights.filter((flight) => (flight.predicted_delay_minutes || 0) >= 15).length;
        const beforeTotal = flights.reduce((sum, flight) => sum + (flight.predicted_delay_minutes || 0), 0);
        const saved = summary.prevented_delay_minutes || 0;
        const afterDelayed = Math.max(0, beforeDelayed - Math.max(1, Math.round((summary.high_risk_count || 0) * 0.6)));
        const afterTotal = Math.max(0, beforeTotal - saved);
        const efficiency = beforeTotal ? Math.round((saved / beforeTotal) * 100) : 0;
        const resource = clampValue(55 + Math.round((summary.average_risk || 0) * 0.35), 55, 95);
        const cost = `$${(saved * 0.08).toFixed(1)}k`;
        const satisfaction = `+${clampValue(Math.round(efficiency * 0.45), 4, 35)}%`;

        setText('horizon-before-delayed', beforeDelayed);
        setText('horizon-after-delayed', afterDelayed);
        setText('horizon-impact-saved', formatMinutes(saved));

        setText('impact-before-delayed', beforeDelayed);
        setText('impact-before-total', formatMinutes(beforeTotal));
        setText('impact-after-delayed', afterDelayed);
        setText('impact-after-total', formatMinutes(afterTotal));
        setText('impact-saved', formatMinutes(saved));
        setText('impact-efficiency', `${efficiency}%`);
        setText('impact-resource', `${resource}%`);
        setText('impact-cost', cost);
        setText('impact-satisfaction', satisfaction);
    } catch (error) {
        console.error('Error loading impact metrics:', error);
    }
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}
