// ============================================================================
// EVENT DETAIL PAGE LOGIC (event_detail.html)
// ============================================================================

let eventSelectedRecommendations = new Set();
let eventCurrentRisk = 0;
let eventIndex = null;
let currentEvent = null;

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('event-detail-title')) {
        initEventDetailPage();
    }
});

async function initEventDetailPage() {
    const pathParts = window.location.pathname.split('/');
    eventIndex = parseInt(pathParts[pathParts.length - 1]);
    
    if (isNaN(eventIndex)) return;

    try {
        const response = await fetch('/api/predict/events', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ time_horizon: 0 })
        });
        const data = await response.json();
        const event = (data.events || [])[eventIndex] || null;
        currentEvent = event;
        
        if (event) {
            renderEventDetailUI(event);
        } else {
            document.getElementById('event-detail-title').textContent = 'Event Not Found';
        }
    } catch (error) {
        console.error('Error loading event detail:', error);
        document.getElementById('event-detail-title').textContent = 'Event Not Found';
    }
}

function renderEventDetailUI(event) {
    eventCurrentRisk = event.risk;
    
    document.getElementById('event-detail-title').textContent = event.text;
    document.getElementById('event-detail-time').textContent = `${event.time} • ${event.type.toUpperCase()}`;
    
    const riskColor = getRiskColor(event.risk);
    const badge = document.getElementById('event-detail-badge');
    badge.textContent = getPriorityLabel(event.risk);
    badge.className = `px-3 py-1 ${getBadgeClass(event.risk)} text-white text-xs font-bold rounded uppercase`;
    
    const scoreEl = document.getElementById('event-detail-risk');
    scoreEl.textContent = event.risk;
    scoreEl.className = `text-3xl font-bold ${riskColor}`;
    
    document.getElementById('event-detail-circle').setAttribute('stroke', event.risk >= 80 ? '#ef4444' : (event.risk >= 50 ? '#f97316' : '#22c55e'));
    document.getElementById('event-detail-delay').textContent = Math.floor(event.risk * 0.5) + 'm';
    document.getElementById('event-detail-confidence').textContent = Math.floor(80 + Math.random() * 15) + '%';
    document.getElementById('event-detail-impact').textContent = event.impact;
    
    renderEventRecommendations(event);
    updateEventApplyButton();
}

function renderEventRecommendations(event) {
    const container = document.getElementById('event-detail-recommendations');
    container.innerHTML = '';
    eventSelectedRecommendations.clear();
    
    const recs = event.recommendations || [];
    
    recs.forEach(rec => {
        const card = document.createElement('div');
        card.className = 'rec-card border border-slate-700 bg-slate-800/50';
        card.dataset.recId = rec.id;
        card.onclick = () => toggleEventRecommendation(rec.id, card);
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

function toggleEventRecommendation(recId, cardElement) {
    if (eventSelectedRecommendations.has(recId)) {
        eventSelectedRecommendations.delete(recId);
        cardElement.classList.remove('selected', 'border-blue-500', 'bg-blue-900/20');
        cardElement.classList.add('border-slate-700', 'bg-slate-800/50');
    } else {
        eventSelectedRecommendations.add(recId);
        cardElement.classList.add('selected', 'border-blue-500', 'bg-blue-900/20');
        cardElement.classList.remove('border-slate-700', 'bg-slate-800/50');
    }
    updateEventExpectedImpact();
    updateEventApplyButton();
}

function selectAllEventRecommendations() {
    document.querySelectorAll('#event-detail-recommendations .rec-card').forEach(card => {
        eventSelectedRecommendations.add(card.dataset.recId);
        card.classList.add('selected', 'border-blue-500', 'bg-blue-900/20');
        card.classList.remove('border-slate-700', 'bg-slate-800/50');
    });
    updateEventExpectedImpact();
    updateEventApplyButton();
}

function updateEventExpectedImpact() {
    const event = currentEvent;
    const recs = event ? (event.recommendations || []) : [];
    
    let totalRiskReduction = 0, totalDelayReduction = 0;
    eventSelectedRecommendations.forEach(recId => {
        const rec = recs.find(r => r.id === recId);
        if (rec) { 
            totalRiskReduction += rec.riskReduction; 
            totalDelayReduction += rec.delayReduction; 
        }
    });
    
    const newRisk = Math.max(0, eventCurrentRisk - totalRiskReduction);
    document.getElementById('event-expected-delay').textContent = totalDelayReduction + 'm';
    document.getElementById('event-expected-risk').textContent = newRisk + '%';
}

function updateEventApplyButton() {
    const btn = document.getElementById('event-apply-btn');
    if (eventSelectedRecommendations.size === 0) {
        btn.disabled = true;
        btn.textContent = 'Select at least one recommendation';
    } else {
        btn.disabled = false;
        btn.textContent = `Apply ${eventSelectedRecommendations.size} Recommendation${eventSelectedRecommendations.size > 1 ? 's' : ''}`;
    }
}

async function applyEventRecommendations() {
    const btn = document.getElementById('event-apply-btn');
    btn.textContent = 'Applying...';
    btn.disabled = true;
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const event = currentEvent;
    const recs = event ? (event.recommendations || []) : [];
    
    let totalRiskReduction = 0, totalDelayReduction = 0;
    eventSelectedRecommendations.forEach(recId => {
        const rec = recs.find(r => r.id === recId);
        if (rec) { 
            totalRiskReduction += rec.riskReduction; 
            totalDelayReduction += rec.delayReduction; 
        }
    });
    
    const newRisk = Math.max(0, eventCurrentRisk - totalRiskReduction);
    eventCurrentRisk = newRisk;
    
    document.getElementById('event-detail-risk').textContent = newRisk;
    document.getElementById('event-detail-risk').className = `text-3xl font-bold ${getRiskColor(newRisk)}`;
    document.getElementById('event-detail-circle').setAttribute('stroke', newRisk >= 80 ? '#ef4444' : (newRisk >= 50 ? '#f97316' : '#22c55e'));
    
    const badge = document.getElementById('event-detail-badge');
    badge.textContent = getPriorityLabel(newRisk);
    badge.className = `px-3 py-1 ${getBadgeClass(newRisk)} text-white text-xs font-bold rounded uppercase`;
    
    btn.textContent = '✓ Applied Successfully!';
    btn.classList.add('bg-green-600');
    
    setTimeout(() => {
        btn.textContent = 'Select at least one recommendation';
        btn.classList.remove('bg-green-600');
        btn.disabled = false;
        eventSelectedRecommendations.clear();
        renderEventRecommendations(event);
        updateEventApplyButton();
    }, 2000);
}