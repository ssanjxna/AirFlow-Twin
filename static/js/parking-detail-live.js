// ============================================================================
// DATABASE-BACKED PARKING DETAIL
// ============================================================================

let parkingLiveSelectedRecommendations = new Set();
let parkingLiveData = null;

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('parking-badge')) {
        initParkingDetailLivePage();
    }
});

async function initParkingDetailLivePage() {
    try {
        const data = await fetchLiveJson('/api/parking_status');
        parkingLiveData = data;
        renderParkingDetailLive(data);
    } catch (error) {
        console.error('Error loading live parking detail:', error);
        document.getElementById('parking-cause').textContent = 'Unable to load parking analysis right now.';
        document.getElementById('parking-recommendations').innerHTML = '<div class="text-sm text-slate-400">No recommendation data available.</div>';
    }
}

function renderParkingDetailLive(data) {
    const risk = Math.round(data.congestion_score || 0);

    document.getElementById('parking-risk-score').textContent = risk;
    document.getElementById('parking-occupancy').textContent = `${Math.round(data.current_occupancy_rate || 0)}%`;
    document.getElementById('parking-delay').textContent = `${Math.round(data.estimated_delay_minutes || 0)}m`;
    document.getElementById('parking-cause').textContent = data.cause || 'Parking activity is elevated around terminal access.';
    document.getElementById('parking-circle').setAttribute('stroke', getRiskStrokeColor(risk));
    updateCircularProgress('parking-circle', risk);

    const badge = document.getElementById('parking-badge');
    badge.textContent = getPriorityLabel(risk);
    badge.className = `px-3 py-1 ${getBadgeClass(risk)} text-white text-xs font-bold rounded uppercase`;

    document.getElementById('parking-expected-congestion').textContent = `${Math.round(data.expected_impact?.estimated_delay_reduction_minutes || 0)}m`;
    document.getElementById('parking-expected-risk').textContent = `${Math.round(data.expected_impact?.estimated_risk_after_actions_percent || risk)}%`;

    renderParkingRecommendations(data.recommendation_cards || []);
    updateParkingApplyButton();
}

function renderParkingRecommendations(recommendations) {
    const container = document.getElementById('parking-recommendations');
    if (!container) return;

    container.innerHTML = '';
    parkingLiveSelectedRecommendations.clear();

    if (!recommendations.length) {
        container.innerHTML = '<div class="text-sm text-slate-400">All current parking recommendations have already been executed.</div>';
        return;
    }

    recommendations.forEach((rec) => {
        const card = document.createElement('div');
        card.className = 'rec-card border border-slate-700 bg-slate-800/50';
        card.dataset.recId = rec.id;
        card.onclick = () => toggleParkingRecommendation(rec.id, card);
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

function toggleParkingRecommendation(recId, cardElement) {
    if (parkingLiveSelectedRecommendations.has(recId)) {
        parkingLiveSelectedRecommendations.delete(recId);
        cardElement.classList.remove('selected', 'border-blue-500', 'bg-blue-900/20');
        cardElement.classList.add('border-slate-700', 'bg-slate-800/50');
    } else {
        parkingLiveSelectedRecommendations.add(recId);
        cardElement.classList.add('selected', 'border-blue-500', 'bg-blue-900/20');
        cardElement.classList.remove('border-slate-700', 'bg-slate-800/50');
    }
    updateParkingExpectedImpact();
    updateParkingApplyButton();
}

function selectAllParkingRecommendations() {
    document.querySelectorAll('#parking-recommendations .rec-card').forEach((card) => {
        parkingLiveSelectedRecommendations.add(card.dataset.recId);
        card.classList.add('selected', 'border-blue-500', 'bg-blue-900/20');
        card.classList.remove('border-slate-700', 'bg-slate-800/50');
    });
    updateParkingExpectedImpact();
    updateParkingApplyButton();
}

function updateParkingExpectedImpact() {
    if (!parkingLiveData) return;

    let totalRiskReduction = 0;
    let totalDelayReduction = 0;
    const recommendations = parkingLiveData.recommendation_cards || [];

    parkingLiveSelectedRecommendations.forEach((recId) => {
        const rec = recommendations.find((item) => item.id === recId);
        if (rec) {
            totalRiskReduction += rec.risk_reduction;
            totalDelayReduction += rec.delay_reduction;
        }
    });

    const currentRisk = Math.round(parkingLiveData.congestion_score || 0);
    const fallbackDelay = Math.round(parkingLiveData.expected_impact?.estimated_delay_reduction_minutes || 0);
    document.getElementById('parking-expected-congestion').textContent = `${totalDelayReduction || fallbackDelay}m`;
    document.getElementById('parking-expected-risk').textContent = `${Math.max(0, currentRisk - totalRiskReduction)}%`;
}

function updateParkingApplyButton() {
    const btn = document.getElementById('parking-apply-btn');
    if (!btn) return;

    if (!parkingLiveData?.recommendation_cards?.length) {
        btn.disabled = true;
        btn.textContent = 'No pending recommendations';
        return;
    }

    if (parkingLiveSelectedRecommendations.size === 0) {
        btn.disabled = true;
        btn.textContent = 'Select at least one recommendation';
    } else {
        btn.disabled = false;
        btn.textContent = `Apply ${parkingLiveSelectedRecommendations.size} Recommendation${parkingLiveSelectedRecommendations.size > 1 ? 's' : ''}`;
    }
}

async function applyParkingRecommendations() {
    if (!parkingLiveData) return;

    const btn = document.getElementById('parking-apply-btn');
    btn.textContent = 'Applying...';
    btn.disabled = true;

    try {
        const data = await fetchLiveJson('/api/parking/apply_recommendations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action_ids: [...parkingLiveSelectedRecommendations],
                operator_id: 'dashboard_user',
            }),
        });

        parkingLiveData = data;
        renderParkingDetailLive(data);
        try {
            await refreshRememberedLiveState();
        } catch (refreshError) {
            console.error('Error refreshing shared live state:', refreshError);
            refreshShellMetrics();
        }

        btn.textContent = 'Applied Successfully';
        btn.classList.add('bg-green-600');
    } catch (error) {
        console.error('Error applying parking recommendations:', error);
        btn.textContent = 'Apply failed';
        btn.classList.add('bg-red-600');
    }

    setTimeout(() => {
        btn.classList.remove('bg-green-600', 'bg-red-600');
        updateParkingApplyButton();
    }, 1200);
}
