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
        const data = await fetchLiveJson('/api/impact_summary');

        const beforeDelayed = data.before_delayed || 0;
        const beforeTotal = data.before_total_delay || 0;
        const afterDelayed = data.after_delayed || 0;
        const afterTotal = data.after_total_delay || 0;
        const saved = data.total_time_saved || 0;
        const efficiency = data.efficiency_improvement || 0;
        const resource = data.resource_optimization || 0;
        const cost = `$${Number(data.cost_savings_k || 0).toFixed(1)}k`;
        const satisfaction = `+${data.passenger_satisfaction_gain || 0}%`;

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
