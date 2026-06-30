// ============================================================================
// LIVE EVENT DETAIL OVERRIDES
// ============================================================================

let eventLiveSelectedRecommendations = new Set();
let eventLiveCurrentRisk = 0;
let eventLiveData = null;

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('event-detail-title')) {
        initEventDetailLivePage();
    }
});

async function initEventDetailLivePage() {
    const pathParts = window.location.pathname.split('/');
    const eventIndex = parseInt(pathParts[pathParts.length - 1], 10);
    const rememberedEvents = loadRememberedHorizonEvents();
    eventLiveData = loadSelectedHorizonEvent() || rememberedEvents[eventIndex] || rememberedEvents[0] || null;

    if (!eventLiveData) {
        document.getElementById('event-detail-title').textContent = 'Event Not Found';
        document.getElementById('event-detail-impact').textContent = 'No live horizon event data is available for this view.';
        return;
    }

    renderEventDetailLiveUI(eventLiveData);
}

function renderEventDetailLiveUI(event) {
    eventLiveCurrentRisk = event.risk;
    document.getElementById('event-detail-title').textContent = event.text;
    document.getElementById('event-detail-time').textContent = `${event.time} • ${String(event.type || 'event').toUpperCase()}`;
    document.getElementById('event-detail-impact').textContent = event.impact;
    document.getElementById('event-detail-delay').textContent = `${Math.max(6, Math.round(event.risk * 0.45))}m`;
    document.getElementById('event-detail-confidence').textContent = `${Math.max(72, Math.min(97, event.risk + 8))}%`;

    const badge = document.getElementById('event-detail-badge');
    badge.textContent = getPriorityLabel(event.risk);
    badge.className = `px-3 py-1 ${getBadgeClass(event.risk)} text-white text-xs font-bold rounded uppercase`;

    document.getElementById('event-detail-risk').textContent = event.risk;
    document.getElementById('event-detail-circle').setAttribute('stroke', getRiskStrokeColor(event.risk));
    updateCircularProgress('event-detail-circle', event.risk);

    renderEventLiveRecommendations(event.recommendations || []);
    updateEventApplyButton();
}

function renderEventLiveRecommendations(recommendations) {
    const container = document.getElementById('event-detail-recommendations');
    if (!container) return;
    container.innerHTML = '';
    eventLiveSelectedRecommendations.clear();

    recommendations.forEach((rec) => {
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
    if (eventLiveSelectedRecommendations.has(recId)) {
        eventLiveSelectedRecommendations.delete(recId);
        cardElement.classList.remove('selected', 'border-blue-500', 'bg-blue-900/20');
        cardElement.classList.add('border-slate-700', 'bg-slate-800/50');
    } else {
        eventLiveSelectedRecommendations.add(recId);
        cardElement.classList.add('selected', 'border-blue-500', 'bg-blue-900/20');
        cardElement.classList.remove('border-slate-700', 'bg-slate-800/50');
    }
    updateEventExpectedImpact();
    updateEventApplyButton();
}

function selectAllEventRecommendations() {
    document.querySelectorAll('#event-detail-recommendations .rec-card').forEach((card) => {
        eventLiveSelectedRecommendations.add(card.dataset.recId);
        card.classList.add('selected', 'border-blue-500', 'bg-blue-900/20');
        card.classList.remove('border-slate-700', 'bg-slate-800/50');
    });
    updateEventExpectedImpact();
    updateEventApplyButton();
}

function updateEventExpectedImpact() {
    const recommendations = eventLiveData?.recommendations || [];
    let totalRiskReduction = 0;
    let totalDelayReduction = 0;

    eventLiveSelectedRecommendations.forEach((recId) => {
        const rec = recommendations.find((item) => item.id === recId);
        if (rec) {
            totalRiskReduction += rec.riskReduction;
            totalDelayReduction += rec.delayReduction;
        }
    });

    document.getElementById('event-expected-delay').textContent = `${totalDelayReduction}m`;
    document.getElementById('event-expected-risk').textContent = `${Math.max(0, eventLiveCurrentRisk - totalRiskReduction)}%`;
}

function updateEventApplyButton() {
    const btn = document.getElementById('event-apply-btn');
    if (!btn) return;

    if (eventLiveSelectedRecommendations.size === 0) {
        btn.disabled = true;
        btn.textContent = 'Select at least one recommendation';
    } else {
        btn.disabled = false;
        btn.textContent = `Apply ${eventLiveSelectedRecommendations.size} Recommendation${eventLiveSelectedRecommendations.size > 1 ? 's' : ''}`;
    }
}

async function applyEventRecommendations() {
    const btn = document.getElementById('event-apply-btn');
    btn.textContent = 'Applying...';
    btn.disabled = true;

    await new Promise((resolve) => setTimeout(resolve, 600));

    let totalRiskReduction = 0;
    eventLiveSelectedRecommendations.forEach((recId) => {
        const rec = (eventLiveData?.recommendations || []).find((item) => item.id === recId);
        if (rec) totalRiskReduction += rec.riskReduction;
    });

    eventLiveCurrentRisk = Math.max(0, eventLiveCurrentRisk - totalRiskReduction);
    renderEventDetailLiveUI({ ...eventLiveData, risk: eventLiveCurrentRisk });
    btn.textContent = 'Applied Successfully';
    btn.classList.add('bg-green-600');

    setTimeout(() => {
        btn.classList.remove('bg-green-600');
        updateEventApplyButton();
    }, 1200);
}
