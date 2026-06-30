// ============================================================================
// LIVE FLIGHT DETAIL OVERRIDES
// ============================================================================

let flightDetailData = null;
let flightDetailSelectedRecommendations = new Set();

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('detail-flight-id')) {
        initFlightDetailLivePage();
    }
});

async function initFlightDetailLivePage() {
    const flightId = window.location.pathname.split('/').pop();

    try {
        const response = await fetch(`/api/flight/${flightId}/detail`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Flight detail unavailable');
        }

        flightDetailData = data;
        renderFlightDetailLive(data);
    } catch (error) {
        console.error('Error loading flight detail:', error);
        document.getElementById('detail-risk-cause').textContent = 'Unable to load AI analysis for this flight right now.';
        document.getElementById('detail-ai-recommendations').innerHTML = '<div class="text-sm text-slate-400">No recommendation data available.</div>';
    }
}

function renderFlightDetailLive(data) {
    const flight = data.flight;
    const risk = Math.round(flight.risk || 0);
    const circleOffset = Math.max(0, 251 - (251 * risk / 100));

    document.getElementById('detail-flight-id').textContent = flight.id;
    document.getElementById('detail-flight-route').textContent = `${flight.origin} → ${flight.destination}`;
    document.getElementById('detail-risk-score').textContent = risk;
    document.getElementById('detail-risk-circle').setAttribute('stroke', risk >= 80 ? '#ef4444' : (risk >= 50 ? '#f97316' : '#22c55e'));
    document.getElementById('detail-risk-circle').setAttribute('stroke-dashoffset', String(circleOffset));
    document.getElementById('detail-predicted-delay').textContent = `${flight.predicted_delay_minutes}m`;
    document.getElementById('detail-confidence').textContent = `${flight.confidence_percent}%`;
    document.getElementById('detail-risk-cause').textContent = data.risk_cause || data.executive_summary || 'Operational risk analysis is available.';

    const badge = document.getElementById('detail-risk-badge');
    badge.textContent = getPriorityLabel(risk);
    badge.className = `px-3 py-1 ${getBadgeClass(risk)} text-white text-xs font-bold rounded uppercase`;

    document.getElementById('detail-expected-delay').textContent = `${Math.round(data.expected_impact?.estimated_delay_reduction_minutes || 0)}m`;
    document.getElementById('detail-expected-risk').textContent = `${Math.round(data.expected_impact?.estimated_risk_after_actions_percent || risk)}%`;

    renderFlightDetailRecommendations(data.recommendations || []);
    updateFlightDetailApplyButton();
}

function renderFlightDetailRecommendations(recommendations) {
    const container = document.getElementById('detail-ai-recommendations');
    if (!container) return;

    container.innerHTML = '';
    flightDetailSelectedRecommendations.clear();

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
                <div class="rec-impact text-xs mt-1">${rec.target_team} · ${rec.impact}</div>
            </div>
        `;
        container.appendChild(card);
    });
}

function toggleFlightDetailRecommendation(recId, cardElement) {
    if (flightDetailSelectedRecommendations.has(recId)) {
        flightDetailSelectedRecommendations.delete(recId);
        cardElement.classList.remove('selected', 'border-blue-500', 'bg-blue-900/20');
        cardElement.classList.add('border-slate-700', 'bg-slate-800/50');
    } else {
        flightDetailSelectedRecommendations.add(recId);
        cardElement.classList.add('selected', 'border-blue-500', 'bg-blue-900/20');
        cardElement.classList.remove('border-slate-700', 'bg-slate-800/50');
    }
    updateFlightDetailExpectedImpact();
    updateFlightDetailApplyButton();
}

function selectAllRecommendationsDetail() {
    document.querySelectorAll('#detail-ai-recommendations .rec-card').forEach((card) => {
        flightDetailSelectedRecommendations.add(card.dataset.recId);
        card.classList.add('selected', 'border-blue-500', 'bg-blue-900/20');
        card.classList.remove('border-slate-700', 'bg-slate-800/50');
    });
    updateFlightDetailExpectedImpact();
    updateFlightDetailApplyButton();
}

function updateFlightDetailExpectedImpact() {
    if (!flightDetailData) return;

    let totalDelayReduction = 0;
    let totalRiskReduction = 0;
    const recommendations = flightDetailData.recommendations || [];

    flightDetailSelectedRecommendations.forEach((recId) => {
        const rec = recommendations.find((item) => item.id === recId);
        if (rec) {
            totalDelayReduction += rec.delay_reduction;
            totalRiskReduction += rec.risk_reduction;
        }
    });

    const currentRisk = Math.round(flightDetailData.flight?.risk || 0);
    document.getElementById('detail-expected-delay').textContent = `${totalDelayReduction || Math.round(flightDetailData.expected_impact?.estimated_delay_reduction_minutes || 0)}m`;
    document.getElementById('detail-expected-risk').textContent = `${Math.max(0, currentRisk - totalRiskReduction)}%`;
}

function updateFlightDetailApplyButton() {
    const btn = document.getElementById('detail-apply-btn');
    if (!btn) return;

    if (flightDetailSelectedRecommendations.size === 0) {
        btn.disabled = true;
        btn.textContent = 'Select at least one recommendation';
    } else {
        btn.disabled = false;
        btn.textContent = `Apply ${flightDetailSelectedRecommendations.size} Recommendation${flightDetailSelectedRecommendations.size > 1 ? 's' : ''}`;
    }
}

async function applySelectedRecommendationsDetail() {
    if (!flightDetailData) return;

    const btn = document.getElementById('detail-apply-btn');
    btn.textContent = 'Applying...';
    btn.disabled = true;

    await new Promise((resolve) => setTimeout(resolve, 700));

    let totalDelayReduction = 0;
    let totalRiskReduction = 0;
    const recommendations = flightDetailData.recommendations || [];
    flightDetailSelectedRecommendations.forEach((recId) => {
        const rec = recommendations.find((item) => item.id === recId);
        if (rec) {
            totalDelayReduction += rec.delay_reduction;
            totalRiskReduction += rec.risk_reduction;
        }
    });

    const newRisk = Math.max(0, Math.round((flightDetailData.flight?.risk || 0) - totalRiskReduction));
    const newDelay = Math.max(0, Math.round((flightDetailData.flight?.predicted_delay_minutes || 0) - totalDelayReduction));

    flightDetailData.flight.risk = newRisk;
    flightDetailData.flight.predicted_delay_minutes = newDelay;
    renderFlightDetailLive(flightDetailData);

    btn.textContent = 'Applied Successfully';
    btn.classList.add('bg-green-600');

    setTimeout(() => {
        btn.classList.remove('bg-green-600');
        updateFlightDetailApplyButton();
    }, 1200);
}
