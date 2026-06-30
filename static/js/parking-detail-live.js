// ============================================================================
// LIVE PARKING DETAIL OVERRIDES
// ============================================================================

let parkingLiveSelectedRecommendations = new Set();
let parkingLiveCurrentRisk = 0;
let parkingLiveRecommendations = [];

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('parking-badge')) {
        initParkingDetailLivePage();
    }
});

async function initParkingDetailLivePage() {
    try {
        const response = await fetch('/api/parking_status');
        const data = await response.json();

        parkingLiveCurrentRisk = Math.round(data.congestion_score || 0);
        parkingLiveRecommendations = buildParkingRecommendationCards(data.recommendations, parkingLiveCurrentRisk);

        document.getElementById('parking-risk-score').textContent = parkingLiveCurrentRisk;
        document.getElementById('parking-occupancy').textContent = `${Math.round(data.current_occupancy_rate || 0)}%`;
        document.getElementById('parking-delay').textContent = `${Math.round(data.estimated_delay_minutes || 0)}m`;
        document.getElementById('parking-cause').textContent = data.cause || 'Parking activity is elevated around terminal access.';
        document.getElementById('parking-circle').setAttribute('stroke', parkingLiveCurrentRisk >= 80 ? '#ef4444' : (parkingLiveCurrentRisk >= 50 ? '#f97316' : '#22c55e'));

        const badge = document.getElementById('parking-badge');
        badge.textContent = getPriorityLabel(parkingLiveCurrentRisk);
        badge.className = `px-3 py-1 ${getBadgeClass(parkingLiveCurrentRisk)} text-white text-xs font-bold rounded uppercase`;

        renderParkingRecommendations();
        updateParkingApplyButton();
    } catch (error) {
        console.error('Error loading live parking detail:', error);
    }
}

function renderParkingRecommendations() {
    const container = document.getElementById('parking-recommendations');
    if (!container) return;
    container.innerHTML = '';
    parkingLiveSelectedRecommendations.clear();

    parkingLiveRecommendations.forEach((rec) => {
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
                <div class="rec-impact text-xs mt-1">${rec.impact}</div>
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
    let totalRiskReduction = 0;
    let totalDelayReduction = 0;

    parkingLiveSelectedRecommendations.forEach((recId) => {
        const rec = parkingLiveRecommendations.find((item) => item.id === recId);
        if (rec) {
            totalRiskReduction += rec.riskReduction;
            totalDelayReduction += rec.delayReduction;
        }
    });

    const newRisk = Math.max(0, parkingLiveCurrentRisk - totalRiskReduction);
    document.getElementById('parking-expected-congestion').textContent = `${totalDelayReduction}m`;
    document.getElementById('parking-expected-risk').textContent = `${newRisk}%`;
}

function updateParkingApplyButton() {
    const btn = document.getElementById('parking-apply-btn');
    if (!btn) return;

    if (parkingLiveSelectedRecommendations.size === 0) {
        btn.disabled = true;
        btn.textContent = 'Select at least one recommendation';
    } else {
        btn.disabled = false;
        btn.textContent = `Apply ${parkingLiveSelectedRecommendations.size} Recommendation${parkingLiveSelectedRecommendations.size > 1 ? 's' : ''}`;
    }
}

async function applyParkingRecommendations() {
    const btn = document.getElementById('parking-apply-btn');
    btn.textContent = 'Applying...';
    btn.disabled = true;

    await new Promise((resolve) => setTimeout(resolve, 600));

    let totalRiskReduction = 0;
    let totalDelayReduction = 0;
    parkingLiveSelectedRecommendations.forEach((recId) => {
        const rec = parkingLiveRecommendations.find((item) => item.id === recId);
        if (rec) {
            totalRiskReduction += rec.riskReduction;
            totalDelayReduction += rec.delayReduction;
        }
    });

    parkingLiveCurrentRisk = Math.max(0, parkingLiveCurrentRisk - totalRiskReduction);
    document.getElementById('parking-risk-score').textContent = parkingLiveCurrentRisk;
    document.getElementById('parking-delay').textContent = `${Math.max(0, Math.round((parkingLiveCurrentRisk * 0.22)))}m`;
    document.getElementById('parking-circle').setAttribute('stroke', parkingLiveCurrentRisk >= 80 ? '#ef4444' : (parkingLiveCurrentRisk >= 50 ? '#f97316' : '#22c55e'));

    const badge = document.getElementById('parking-badge');
    badge.textContent = getPriorityLabel(parkingLiveCurrentRisk);
    badge.className = `px-3 py-1 ${getBadgeClass(parkingLiveCurrentRisk)} text-white text-xs font-bold rounded uppercase`;

    document.getElementById('parking-expected-congestion').textContent = `${totalDelayReduction}m`;
    document.getElementById('parking-expected-risk').textContent = `${parkingLiveCurrentRisk}%`;

    btn.textContent = 'Applied Successfully';
    btn.classList.add('bg-green-600');

    setTimeout(() => {
        btn.classList.remove('bg-green-600');
        renderParkingRecommendations();
        updateParkingApplyButton();
    }, 1200);
}
