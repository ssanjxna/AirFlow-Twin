// ============================================================================
// DATABASE-BACKED FLIGHT DETAIL
// ============================================================================

let flightDetailDbData = null;
let flightDetailDbSelectedRecommendations = new Set();

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('detail-flight-id')) {
        initFlightDetailDbPage();
    }
});

async function initFlightDetailDbPage() {
    const flightId = window.location.pathname.split('/').pop();

    try {
        const data = await fetchLiveJson(`/api/flight/${flightId}/detail`);
        flightDetailDbData = data;
        renderFlightDetailDb(data);
    } catch (error) {
        console.error('Error loading flight detail:', error);
        document.getElementById('detail-risk-cause').textContent = 'Unable to load AI analysis for this flight right now.';
        document.getElementById('detail-ai-recommendations').innerHTML = '<div class="text-sm text-slate-400">No recommendation data available.</div>';
    }
}

function renderFlightDetailDb(data) {
    const flight = data.flight;
    const risk = Math.round(flight.risk || 0);

    document.getElementById('detail-flight-id').textContent = flight.id;
    document.getElementById('detail-flight-route').textContent = `${flight.origin} -> ${flight.destination}`;
    document.getElementById('detail-risk-score').textContent = risk;
    document.getElementById('detail-risk-circle').setAttribute('stroke', getRiskStrokeColor(risk));
    updateCircularProgress('detail-risk-circle', risk);
    document.getElementById('detail-predicted-delay').textContent = `${flight.predicted_delay_minutes}m`;
    document.getElementById('detail-confidence').textContent = `${flight.confidence_percent}%`;
    document.getElementById('detail-risk-cause').textContent = data.risk_cause || data.executive_summary || 'Operational risk analysis is available.';

    const badge = document.getElementById('detail-risk-badge');
    badge.textContent = getPriorityLabel(risk);
    badge.className = `px-3 py-1 ${getBadgeClass(risk)} text-white text-xs font-bold rounded uppercase`;

    document.getElementById('detail-expected-delay').textContent = `${Math.round(data.expected_impact?.estimated_delay_reduction_minutes || 0)}m`;
    document.getElementById('detail-expected-risk').textContent = `${Math.round(data.expected_impact?.estimated_risk_after_actions_percent || risk)}%`;

    renderFlightDetailDbRecommendations(data.recommendations || []);
    updateFlightDetailDbApplyButton();
}

function renderFlightDetailDbRecommendations(recommendations) {
    const container = document.getElementById('detail-ai-recommendations');
    if (!container) return;

    container.innerHTML = '';
    flightDetailDbSelectedRecommendations.clear();

    if (!recommendations.length) {
        container.innerHTML = '<div class="text-sm text-slate-400">All current recommendations for this flight have already been executed.</div>';
        return;
    }

    recommendations.forEach((rec) => {
        const card = document.createElement('div');
        card.className = 'rec-card border border-slate-700 bg-slate-800/50';
        card.dataset.recId = rec.id;
        card.onclick = () => toggleFlightDetailRecommendation(rec.id, card);
        card.innerHTML = `
            <div class="rec-checkbox mt-1">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>
            </div>
            <div class="rec-content flex-1">
                <div class="rec-text text-sm">${rec.text}</div>
                <div class="rec-impact text-xs mt-1">${rec.target_team} | ${rec.impact}</div>
            </div>
        `;
        container.appendChild(card);
    });
}

function toggleFlightDetailRecommendation(recId, cardElement) {
    if (flightDetailDbSelectedRecommendations.has(recId)) {
        flightDetailDbSelectedRecommendations.delete(recId);
        cardElement.classList.remove('selected', 'border-blue-500', 'bg-blue-900/20');
        cardElement.classList.add('border-slate-700', 'bg-slate-800/50');
    } else {
        flightDetailDbSelectedRecommendations.add(recId);
        cardElement.classList.add('selected', 'border-blue-500', 'bg-blue-900/20');
        cardElement.classList.remove('border-slate-700', 'bg-slate-800/50');
    }
    updateFlightDetailDbExpectedImpact();
    updateFlightDetailDbApplyButton();
}

function selectAllRecommendationsDetail() {
    document.querySelectorAll('#detail-ai-recommendations .rec-card').forEach((card) => {
        flightDetailDbSelectedRecommendations.add(card.dataset.recId);
        card.classList.add('selected', 'border-blue-500', 'bg-blue-900/20');
        card.classList.remove('border-slate-700', 'bg-slate-800/50');
    });
    updateFlightDetailDbExpectedImpact();
    updateFlightDetailDbApplyButton();
}

function updateFlightDetailDbExpectedImpact() {
    if (!flightDetailDbData) return;

    let totalDelayReduction = 0;
    let totalRiskReduction = 0;
    const recommendations = flightDetailDbData.recommendations || [];

    flightDetailDbSelectedRecommendations.forEach((recId) => {
        const rec = recommendations.find((item) => item.id === recId);
        if (rec) {
            totalDelayReduction += rec.delay_reduction;
            totalRiskReduction += rec.risk_reduction;
        }
    });

    const currentRisk = Math.round(flightDetailDbData.flight?.risk || 0);
    const fallbackDelay = Math.round(flightDetailDbData.expected_impact?.estimated_delay_reduction_minutes || 0);
    document.getElementById('detail-expected-delay').textContent = `${totalDelayReduction || fallbackDelay}m`;
    document.getElementById('detail-expected-risk').textContent = `${Math.max(0, currentRisk - totalRiskReduction)}%`;
}

function updateFlightDetailDbApplyButton() {
    const btn = document.getElementById('detail-apply-btn');
    if (!btn) return;

    if (!flightDetailDbData?.recommendations?.length) {
        btn.disabled = true;
        btn.textContent = 'No pending recommendations';
        return;
    }

    if (flightDetailDbSelectedRecommendations.size === 0) {
        btn.disabled = true;
        btn.textContent = 'Select at least one recommendation';
    } else {
        btn.disabled = false;
        btn.textContent = `Apply ${flightDetailDbSelectedRecommendations.size} Recommendation${flightDetailDbSelectedRecommendations.size > 1 ? 's' : ''}`;
    }
}

async function applySelectedRecommendationsDetail() {
    if (!flightDetailDbData) return;

    const btn = document.getElementById('detail-apply-btn');
    btn.textContent = 'Applying...';
    btn.disabled = true;

    try {
        const data = await fetchLiveJson(`/api/flight/${flightDetailDbData.flight.id}/apply_recommendations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action_ids: [...flightDetailDbSelectedRecommendations],
                operator_id: 'dashboard_user',
            }),
        });

        flightDetailDbData = {
            ...flightDetailDbData,
            flight: data.flight,
            risk_cause: data.risk_cause,
            recommendations: data.recommendations,
            completed_recommendations: data.completed_recommendations,
            expected_impact: data.expected_impact,
        };
        renderFlightDetailDb(flightDetailDbData);
        try {
            await refreshRememberedLiveState();
        } catch (refreshError) {
            console.error('Error refreshing shared live state:', refreshError);
            refreshShellMetrics();
        }

        btn.textContent = 'Applied Successfully';
        btn.classList.add('bg-green-600');
    } catch (error) {
        console.error('Error applying recommendations:', error);
        btn.textContent = 'Apply failed';
        btn.classList.add('bg-red-600');
    }

    setTimeout(() => {
        btn.classList.remove('bg-green-600', 'bg-red-600');
        updateFlightDetailDbApplyButton();
    }, 1200);
}
