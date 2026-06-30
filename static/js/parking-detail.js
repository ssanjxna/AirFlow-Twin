// ============================================================================
// PARKING DETAIL PAGE LOGIC (parking_detail.html)
// ============================================================================

let parkingSelectedRecommendations = new Set();
let parkingCurrentRisk = 0;
let parkingRecommendations = [];

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('parking-badge')) {
        initParkingDetailPage();
    }
});

async function initParkingDetailPage() {
    try {
        const response = await fetch('/api/parking_status');
        const data = await response.json();
        
        parkingCurrentRisk = Math.round(data.congestion_score);
        parkingRecommendations = data.recommendations || [];
        
        document.getElementById('parking-risk-score').textContent = parkingCurrentRisk;
        document.getElementById('parking-occupancy').textContent = Math.round(data.current_occupancy_rate) + '%';
        document.getElementById('parking-delay').textContent = Math.round(parkingCurrentRisk * 0.25) + 'm';
        
        const riskColor = getRiskColor(parkingCurrentRisk);
        const badge = document.getElementById('parking-badge');
        badge.textContent = getPriorityLabel(parkingCurrentRisk);
        badge.className = `px-3 py-1 ${getBadgeClass(parkingCurrentRisk)} text-white text-xs font-bold rounded uppercase`;
        
        document.getElementById('parking-circle').setAttribute('stroke', parkingCurrentRisk >= 80 ? '#ef4444' : (parkingCurrentRisk >= 50 ? '#f97316' : '#22c55e'));
        document.getElementById('parking-cause').textContent = data.model_prediction ? `Parking congestion is ${data.status.toLowerCase()} with ${Math.round(data.current_occupancy_rate)}% occupancy and ${Math.round(data.congestion_score)}% model risk.` : `Passenger parking congestion at ${parkingCurrentRisk}%. Heavy vehicle traffic causing bottlenecks.`;
        
        renderParkingRecommendations();
        updateParkingApplyButton();
    } catch (error) {
        console.error('Error loading parking data:', error);
    }
}

function renderParkingRecommendations() {
    const container = document.getElementById('parking-recommendations');
    container.innerHTML = '';
    parkingSelectedRecommendations.clear();
    
    const recs = parkingRecommendations.length ? parkingRecommendations : (recommendationsDB['PARKING'] || []);
    
    recs.forEach(rec => {
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
    if (parkingSelectedRecommendations.has(recId)) {
        parkingSelectedRecommendations.delete(recId);
        cardElement.classList.remove('selected', 'border-blue-500', 'bg-blue-900/20');
        cardElement.classList.add('border-slate-700', 'bg-slate-800/50');
    } else {
        parkingSelectedRecommendations.add(recId);
        cardElement.classList.add('selected', 'border-blue-500', 'bg-blue-900/20');
        cardElement.classList.remove('border-slate-700', 'bg-slate-800/50');
    }
    updateParkingExpectedImpact();
    updateParkingApplyButton();
}

function selectAllParkingRecommendations() {
    document.querySelectorAll('#parking-recommendations .rec-card').forEach(card => {
        parkingSelectedRecommendations.add(card.dataset.recId);
        card.classList.add('selected', 'border-blue-500', 'bg-blue-900/20');
        card.classList.remove('border-slate-700', 'bg-slate-800/50');
    });
    updateParkingExpectedImpact();
    updateParkingApplyButton();
}

function updateParkingExpectedImpact() {
    const recs = parkingRecommendations.length ? parkingRecommendations : (recommendationsDB['PARKING'] || []);
    let totalRiskReduction = 0;
    
    parkingSelectedRecommendations.forEach(recId => {
        const rec = recs.find(r => r.id === recId);
        if (rec) { totalRiskReduction += rec.riskReduction; }
    });
    
    const newRisk = Math.max(0, parkingCurrentRisk - totalRiskReduction);
    const congestionReduction = Math.round((totalRiskReduction / parkingCurrentRisk) * 100);
    
    document.getElementById('parking-expected-congestion').textContent = congestionReduction + '%';
    document.getElementById('parking-expected-risk').textContent = newRisk + '%';
}

function updateParkingApplyButton() {
    const btn = document.getElementById('parking-apply-btn');
    if (parkingSelectedRecommendations.size === 0) {
        btn.disabled = true;
        btn.textContent = 'Select at least one recommendation';
    } else {
        btn.disabled = false;
        btn.textContent = `Apply ${parkingSelectedRecommendations.size} Recommendation${parkingSelectedRecommendations.size > 1 ? 's' : ''}`;
    }
}

async function applyParkingRecommendations() {
    const btn = document.getElementById('parking-apply-btn');
    btn.textContent = 'Applying...';
    btn.disabled = true;
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const recs = parkingRecommendations.length ? parkingRecommendations : (recommendationsDB['PARKING'] || []);
    let totalRiskReduction = 0;
    
    parkingSelectedRecommendations.forEach(recId => {
        const rec = recs.find(r => r.id === recId);
        if (rec) { totalRiskReduction += rec.riskReduction; }
    });
    
    const newRisk = Math.max(0, parkingCurrentRisk - totalRiskReduction);
    parkingCurrentRisk = newRisk;
    
    document.getElementById('parking-risk-score').textContent = newRisk;
    document.getElementById('parking-risk-score').className = `text-3xl font-bold ${getRiskColor(newRisk)}`;
    document.getElementById('parking-circle').setAttribute('stroke', newRisk >= 80 ? '#ef4444' : (newRisk >= 50 ? '#f97316' : '#22c55e'));
    
    const badge = document.getElementById('parking-badge');
    badge.textContent = getPriorityLabel(newRisk);
    badge.className = `px-3 py-1 ${getBadgeClass(newRisk)} text-white text-xs font-bold rounded uppercase`;
    
    document.getElementById('parking-occupancy').textContent = Math.round(newRisk * 0.8) + '%';
    document.getElementById('parking-delay').textContent = Math.round(newRisk * 0.25) + 'm';
    
    btn.textContent = '✓ Applied Successfully!';
    btn.classList.add('bg-green-600');
    
    setTimeout(() => {
        btn.textContent = 'Select at least one recommendation';
        btn.classList.remove('bg-green-600');
        btn.disabled = false;
        parkingSelectedRecommendations.clear();
        renderParkingRecommendations();
        updateParkingApplyButton();
    }, 2000);
}