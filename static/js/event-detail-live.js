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

// ============================================================================
// LIVE EVENT DETAIL DATABASE OVERRIDES
// ============================================================================

let eventLiveResolvedDetail = null;

async function initEventDetailLivePage() {
    const pathParts = window.location.pathname.split('/');
    const eventIndex = parseInt(pathParts[pathParts.length - 1], 10);
    const rememberedEvents = loadRememberedHorizonEvents();
    eventLiveData = loadSelectedHorizonEvent() || rememberedEvents[eventIndex] || rememberedEvents[0] || null;

    if (!eventLiveData) {
        document.getElementById('event-detail-title').textContent = 'Event Not Found';
        document.getElementById('event-detail-impact').textContent = 'No live horizon event data is available for this view.';
        document.getElementById('event-detail-recommendations').innerHTML = '<div class="text-sm text-slate-400">No live recommendation data is available.</div>';
        return;
    }

    renderEventDetailShell(eventLiveData);
    await refreshEventEntityData();
}

async function refreshEventEntityData() {
    const entityType = getEventEntityType(eventLiveData);
    const entityId = getEventEntityId(eventLiveData);

    if (!entityType || !entityId) {
        renderEventDetailLiveUI();
        return;
    }

    try {
        if (entityType === 'parking') {
            eventLiveResolvedDetail = await fetchLiveJson('/api/parking_status');
        } else {
            eventLiveResolvedDetail = await fetchLiveJson(`/api/flight/${entityId}/detail`);
        }
    } catch (error) {
        console.error('Error loading live event detail:', error);
        eventLiveResolvedDetail = null;
    }

    renderEventDetailLiveUI();
    persistUpdatedSelectedEvent();
}

function renderEventDetailShell(event) {
    const risk = Math.round(event?.risk || 0);
    document.getElementById('event-detail-title').textContent = event?.text || 'Operational Event';
    document.getElementById('event-detail-time').textContent = `${event?.time || 'Now'} | ${String(event?.type || 'event').toUpperCase()}`;
    document.getElementById('event-detail-impact').textContent = event?.impact || 'Loading live analysis...';
    document.getElementById('event-detail-delay').textContent = '--';
    document.getElementById('event-detail-confidence').textContent = '--';
    document.getElementById('event-detail-secondary-label').textContent = 'Confidence';
    document.getElementById('event-detail-risk').textContent = risk || '--';
    document.getElementById('event-detail-circle').setAttribute('stroke', getRiskStrokeColor(risk));
    updateCircularProgress('event-detail-circle', risk);

    const badge = document.getElementById('event-detail-badge');
    badge.textContent = getPriorityLabel(risk);
    badge.className = `px-3 py-1 ${getBadgeClass(risk)} text-white text-xs font-bold rounded uppercase`;
}

function renderEventDetailLiveUI() {
    const entityType = getEventEntityType(eventLiveData);
    const risk = getEventLiveRisk();
    const delayMinutes = getEventLiveDelay();
    const secondaryLabel = entityType === 'parking' ? 'Occupancy' : 'Confidence';
    const secondaryValue = entityType === 'parking'
        ? `${Math.round(eventLiveResolvedDetail?.current_occupancy_rate || 0)}%`
        : `${Math.round(eventLiveResolvedDetail?.flight?.confidence_percent || 0)}%`;

    eventLiveCurrentRisk = risk;
    document.getElementById('event-detail-title').textContent = getEventLiveTitle();
    document.getElementById('event-detail-time').textContent = `${eventLiveData?.time || 'Now'} | ${String(getEventLiveType()).toUpperCase()}`;
    document.getElementById('event-detail-impact').textContent = getEventLiveImpactText();
    document.getElementById('event-detail-delay').textContent = `${delayMinutes}m`;
    document.getElementById('event-detail-secondary-label').textContent = secondaryLabel;
    document.getElementById('event-detail-confidence').textContent = secondaryValue;

    const badge = document.getElementById('event-detail-badge');
    badge.textContent = getPriorityLabel(risk);
    badge.className = `px-3 py-1 ${getBadgeClass(risk)} text-white text-xs font-bold rounded uppercase`;

    document.getElementById('event-detail-risk').textContent = risk;
    document.getElementById('event-detail-circle').setAttribute('stroke', getRiskStrokeColor(risk));
    updateCircularProgress('event-detail-circle', risk);

    const expectedImpact = getEventExpectedImpact();
    document.getElementById('event-expected-delay').textContent = `${Math.round(expectedImpact?.estimated_delay_reduction_minutes || 0)}m`;
    document.getElementById('event-expected-risk').textContent = `${Math.round(expectedImpact?.estimated_risk_after_actions_percent || risk)}%`;

    renderEventLiveRecommendations(getEventRecommendations());
    updateEventApplyButton();
}

function getEventLiveTitle() {
    const entityType = getEventEntityType(eventLiveData);
    if (entityType === 'parking') {
        return eventLiveData?.text || 'Parking congestion building near terminal access';
    }

    const flight = eventLiveResolvedDetail?.flight;
    if (!flight) return eventLiveData?.text || 'Flight event';
    return eventLiveData?.text || `${flight.id} turnaround risk at ${flight.gate}`;
}

function getEventLiveType() {
    const entityType = getEventEntityType(eventLiveData);
    if (entityType === 'parking') {
        return String(eventLiveResolvedDetail?.status || eventLiveData?.type || 'warning').toLowerCase();
    }
    if (eventLiveCurrentRisk >= 80) return 'critical';
    if (eventLiveCurrentRisk >= 50) return 'warning';
    return 'info';
}

function getEventRecommendations() {
    if (getEventEntityType(eventLiveData) === 'parking') {
        return eventLiveResolvedDetail?.recommendation_cards || eventLiveData?.recommendations || [];
    }
    return eventLiveResolvedDetail?.recommendations || eventLiveData?.recommendations || [];
}

function getEventExpectedImpact() {
    return eventLiveResolvedDetail?.expected_impact || {};
}

function getEventLiveRisk() {
    if (getEventEntityType(eventLiveData) === 'parking') {
        return Math.round(eventLiveResolvedDetail?.congestion_score ?? eventLiveData?.risk ?? 0);
    }
    return Math.round(eventLiveResolvedDetail?.flight?.risk ?? eventLiveData?.risk ?? 0);
}

function getEventLiveDelay() {
    if (getEventEntityType(eventLiveData) === 'parking') {
        return Math.round(eventLiveResolvedDetail?.estimated_delay_minutes || 0);
    }
    return Math.round(eventLiveResolvedDetail?.flight?.predicted_delay_minutes || 0);
}

function getEventLiveImpactText() {
    if (getEventEntityType(eventLiveData) === 'parking') {
        return eventLiveResolvedDetail?.cause || eventLiveData?.impact || 'Parking activity is elevated around terminal access.';
    }
    return eventLiveResolvedDetail?.risk_cause
        || eventLiveResolvedDetail?.executive_summary
        || eventLiveData?.impact
        || 'Operational risk analysis is available for this event.';
}

function buildUpdatedSelectedEvent() {
    if (!eventLiveData) return null;

    const entityType = getEventEntityType(eventLiveData);
    const updatedEvent = {
        ...eventLiveData,
        entityType,
        entityId: getEventEntityId(eventLiveData),
        risk: getEventLiveRisk(),
        type: getEventLiveType(),
        impact: getEventLiveImpactText(),
        recommendations: getEventRecommendations(),
    };

    if (entityType === 'parking') {
        updatedEvent.detailUrl = '/parking';
        updatedEvent.relatedFlightId = 'PARKING';
    } else {
        updatedEvent.detailUrl = `/flight/${updatedEvent.entityId}`;
        updatedEvent.relatedFlightId = updatedEvent.entityId;
    }

    return updatedEvent;
}

function persistUpdatedSelectedEvent() {
    const updatedEvent = buildUpdatedSelectedEvent();
    if (!updatedEvent) return;

    eventLiveData = updatedEvent;
    rememberSelectedHorizonEvent(updatedEvent);

    const rememberedEvents = loadRememberedHorizonEvents();
    if (!rememberedEvents.length) return;

    const refreshedEvents = rememberedEvents.map((event) => (
        isSameEventEntity(event, updatedEvent) ? { ...event, ...updatedEvent } : event
    ));
    rememberHorizonEvents(refreshedEvents);
}

function renderEventLiveRecommendations(recommendations) {
    const container = document.getElementById('event-detail-recommendations');
    if (!container) return;

    container.innerHTML = '';
    eventLiveSelectedRecommendations.clear();

    if (!recommendations.length) {
        container.innerHTML = '<div class="text-sm text-slate-400">All current recommendations for this event have already been executed.</div>';
        return;
    }

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
                <div class="rec-impact text-xs mt-1">${rec.target_team ? `${rec.target_team} | ` : ''}${rec.impact}</div>
            </div>
        `;
        container.appendChild(card);
    });
}

function updateEventExpectedImpact() {
    const recommendations = getEventRecommendations();
    let totalRiskReduction = 0;
    let totalDelayReduction = 0;

    eventLiveSelectedRecommendations.forEach((recId) => {
        const rec = recommendations.find((item) => item.id === recId);
        if (rec) {
            totalRiskReduction += rec.risk_reduction || 0;
            totalDelayReduction += rec.delay_reduction || 0;
        }
    });

    const expectedImpact = getEventExpectedImpact();
    const fallbackDelay = Math.round(expectedImpact?.estimated_delay_reduction_minutes || 0);
    document.getElementById('event-expected-delay').textContent = `${totalDelayReduction || fallbackDelay}m`;
    document.getElementById('event-expected-risk').textContent = `${Math.max(0, eventLiveCurrentRisk - totalRiskReduction)}%`;
}

function updateEventApplyButton() {
    const btn = document.getElementById('event-apply-btn');
    if (!btn) return;

    if (!getEventRecommendations().length) {
        btn.disabled = true;
        btn.textContent = 'No pending recommendations';
        return;
    }

    if (eventLiveSelectedRecommendations.size === 0) {
        btn.disabled = true;
        btn.textContent = 'Select at least one recommendation';
    } else {
        btn.disabled = false;
        btn.textContent = `Apply ${eventLiveSelectedRecommendations.size} Recommendation${eventLiveSelectedRecommendations.size > 1 ? 's' : ''}`;
    }
}

async function applyEventRecommendations() {
    if (!eventLiveData) return;

    const btn = document.getElementById('event-apply-btn');
    btn.textContent = 'Applying...';
    btn.disabled = true;

    try {
        const entityType = getEventEntityType(eventLiveData);
        const entityId = getEventEntityId(eventLiveData);
        const endpoint = entityType === 'parking'
            ? '/api/parking/apply_recommendations'
            : `/api/flight/${entityId}/apply_recommendations`;
        const data = await fetchLiveJson(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action_ids: [...eventLiveSelectedRecommendations],
                operator_id: 'dashboard_user',
            }),
        });

        if (entityType === 'parking') {
            eventLiveResolvedDetail = data;
        } else {
            eventLiveResolvedDetail = {
                ...eventLiveResolvedDetail,
                flight: data.flight,
                risk_cause: data.risk_cause,
                recommendations: data.recommendations,
                completed_recommendations: data.completed_recommendations,
                expected_impact: data.expected_impact,
            };
        }

        renderEventDetailLiveUI();
        persistUpdatedSelectedEvent();
        try {
            await refreshRememberedLiveState();
        } catch (refreshError) {
            console.error('Error refreshing shared live state:', refreshError);
            refreshShellMetrics();
        }

        btn.textContent = 'Applied Successfully';
        btn.classList.add('bg-green-600');
    } catch (error) {
        console.error('Error applying event recommendations:', error);
        btn.textContent = 'Apply failed';
        btn.classList.add('bg-red-600');
    }

    setTimeout(() => {
        btn.classList.remove('bg-green-600', 'bg-red-600');
        updateEventApplyButton();
    }, 1200);
}
