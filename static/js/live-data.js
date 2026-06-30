// ============================================================================
// LIVE UI CONFIGURATION & SHARED HELPERS
// ============================================================================

const PARKING_ZONE_POSITION = { x: 26, y: 71 };
let currentTimeStep = parseInt(sessionStorage.getItem('airflowCurrentTimeStep') || '0', 10);

function clampValue(value, minimum, maximum) {
    return Math.max(minimum, Math.min(maximum, value));
}

function formatMinutes(minutes) {
    const totalMinutes = Math.max(0, Math.round(Number(minutes) || 0));
    if (totalMinutes < 60) return `${totalMinutes}m`;
    const hours = Math.floor(totalMinutes / 60);
    const mins = totalMinutes % 60;
    return mins === 0 ? `${hours}h` : `${hours}h ${mins}m`;
}

function setCurrentTimeStep(minutes) {
    currentTimeStep = Number(minutes) || 0;
    sessionStorage.setItem('airflowCurrentTimeStep', String(currentTimeStep));
}

function applyHeaderSummary(summary) {
    if (!summary) return;

    const highRiskEl = document.getElementById('high-risk-count');
    const totalFlightsEl = document.getElementById('total-flight-count');
    const predictedDelayEl = document.getElementById('total-predicted-delay');
    const preventedDelayEl = document.getElementById('prevented-delay');

    if (highRiskEl) highRiskEl.textContent = summary.high_risk_count;
    if (totalFlightsEl) totalFlightsEl.textContent = summary.total_flights;
    if (predictedDelayEl) predictedDelayEl.textContent = formatMinutes(summary.predicted_delay_minutes);
    if (preventedDelayEl) preventedDelayEl.textContent = formatMinutes(summary.prevented_delay_minutes);
}

function getRiskStrokeColor(risk) {
    if (risk >= 80) return '#ef4444';
    if (risk >= 50) return '#f97316';
    return '#22c55e';
}

function getRiskPalette(risk) {
    if (risk >= 80) {
        return {
            color: '#ef4444',
            glow: 'rgba(239, 68, 68, 0.95)',
            fillStrong: 'rgba(239, 68, 68, 0.50)',
            fillSoft: 'rgba(239, 68, 68, 0.20)',
            labelClass: 'bg-red-600',
        };
    }
    if (risk >= 50) {
        return {
            color: '#f97316',
            glow: 'rgba(249, 115, 22, 0.9)',
            fillStrong: 'rgba(249, 115, 22, 0.42)',
            fillSoft: 'rgba(249, 115, 22, 0.18)',
            labelClass: 'bg-orange-600',
        };
    }
    return {
        color: '#22c55e',
        glow: 'rgba(34, 197, 94, 0.85)',
        fillStrong: 'rgba(34, 197, 94, 0.35)',
        fillSoft: 'rgba(34, 197, 94, 0.14)',
        labelClass: 'bg-green-600',
    };
}

function updateCircularProgress(circleId, percent) {
    const circle = document.getElementById(circleId);
    if (!circle) return;

    const clampedPercent = clampValue(Number(percent) || 0, 0, 100);
    const dashArray = String(circle.getAttribute('stroke-dasharray') || '251');
    const baseLength = Number(dashArray.split(/[ ,]/)[0]) || 251;
    const circleOffset = Math.max(0, baseLength - (baseLength * clampedPercent / 100));

    circle.setAttribute('stroke-dashoffset', String(circleOffset));
}

async function fetchLiveJson(url, options = {}) {
    const mergedOptions = {
        cache: 'no-store',
        ...options,
        headers: {
            'Cache-Control': 'no-cache',
            Pragma: 'no-cache',
            ...(options.headers || {}),
        },
    };

    const response = await fetch(url, mergedOptions);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data?.error || `Request failed for ${url}`);
    }

    return data;
}

async function refreshShellMetrics() {
    try {
        const data = await fetchLiveJson('/api/flights?limit=24');
        applyHeaderSummary(data.summary);
    } catch (error) {
        console.error('Error refreshing header metrics:', error);
    }
}

function resolveHotspotPosition(flight, index, total = 5) {
    const gate = String(flight.gate || '');
    const gateLetter = (gate[0] || 'B').toUpperCase();
    const gateNumber = parseInt(gate.replace(/\D/g, ''), 10);
    const ratio = Number.isFinite(gateNumber)
        ? clampValue(gateNumber / 60, 0.1, 0.95)
        : clampValue((index + 1) / (Math.max(total, 1) + 1), 0.1, 0.95);

    const yByGate = {
        A: 14,
        B: 20,
        C: 29,
        T: 18,
    };

    return {
        x: Math.round(18 + ratio * 70),
        y: yByGate[gateLetter] || 24,
    };
}

function buildFlightEventRecommendations(flight, rankIndex) {
    const firstDelayReduction = Math.max(6, Math.round((flight.predicted_delay_minutes || 20) * 0.35));
    const secondDelayReduction = Math.max(4, Math.round((flight.predicted_delay_minutes || 20) * 0.2));
    const firstRiskReduction = Math.max(8, 18 - rankIndex * 2);
    const secondRiskReduction = Math.max(6, 12 - rankIndex);

    return [
        {
            id: `${flight.id}-rec-1`,
            text: `Prioritize turnaround support for ${flight.id} at ${flight.gate}.`,
            impact: `-${firstDelayReduction}m delay, -${firstRiskReduction}% risk`,
            riskReduction: firstRiskReduction,
            delayReduction: firstDelayReduction,
        },
        {
            id: `${flight.id}-rec-2`,
            text: `Pre-stage gate, baggage, and boarding teams for ${flight.id}.`,
            impact: `-${secondDelayReduction}m delay, -${secondRiskReduction}% risk`,
            riskReduction: secondRiskReduction,
            delayReduction: secondDelayReduction,
        },
    ];
}

function buildParkingRecommendationCards(recommendations, currentRisk) {
    return (recommendations || []).map((text, index) => {
        const riskReduction = Math.max(8, Math.round(currentRisk * (index === 0 ? 0.18 : 0.12)));
        const delayReduction = Math.max(4, Math.round(currentRisk * (index === 0 ? 0.12 : 0.08)));
        return {
            id: `parking-rec-${index + 1}`,
            text,
            impact: `-${delayReduction}m delay, -${riskReduction}% risk`,
            riskReduction,
            delayReduction,
        };
    });
}

function buildHorizonEvents(flights, parkingData) {
    const sortedFlights = [...(flights || [])].sort((a, b) => b.risk - a.risk);
    const eventOffsets = [15, 30, 60];
    const events = sortedFlights.slice(0, 3).map((flight, index) => ({
        id: `flight-${flight.id}`,
        entityType: 'flight',
        entityId: flight.id,
        detailUrl: `/flight/${flight.id}`,
        time: `+${eventOffsets[index]}m`,
        minutesAhead: eventOffsets[index],
        text: `${flight.id} turnaround risk at ${flight.gate}`,
        type: flight.risk >= 80 ? 'critical' : 'warning',
        risk: flight.risk,
        relatedFlightId: flight.id,
        impact: `${flight.origin} to ${flight.destination} is tracking ${flight.predicted_delay_minutes} minutes of possible disruption.`,
        recommendations: buildFlightEventRecommendations(flight, index),
    }));

    if (parkingData && ['high', 'critical'].includes(String(parkingData.status || '').toLowerCase())) {
        events.unshift({
            id: 'parking-pressure',
            entityType: 'parking',
            entityId: 'PARKING',
            detailUrl: '/parking',
            time: '+10m',
            minutesAhead: 10,
            text: 'Parking congestion building near terminal access',
            type: parkingData.status,
            risk: Math.round(parkingData.congestion_score || 0),
            relatedFlightId: 'PARKING',
            impact: parkingData.cause || 'Arrival traffic is creating parking pressure.',
            recommendations: parkingData.recommendation_cards || buildParkingRecommendationCards(parkingData.recommendations, Math.round(parkingData.congestion_score || 0)),
        });
    }

    return events.sort((a, b) => a.minutesAhead - b.minutesAhead);
}

function rememberHorizonEvents(events) {
    sessionStorage.setItem('airflowHorizonEvents', JSON.stringify(events || []));
}

function loadRememberedHorizonEvents() {
    try {
        return JSON.parse(sessionStorage.getItem('airflowHorizonEvents') || '[]');
    } catch (error) {
        return [];
    }
}

function rememberSelectedHorizonEvent(event) {
    sessionStorage.setItem('airflowSelectedHorizonEvent', JSON.stringify(event || null));
}

function loadSelectedHorizonEvent() {
    try {
        return JSON.parse(sessionStorage.getItem('airflowSelectedHorizonEvent') || 'null');
    } catch (error) {
        return null;
    }
}

function rememberLiveSnapshot(snapshot) {
    sessionStorage.setItem('airflowLiveSnapshot', JSON.stringify(snapshot || null));
}

function loadRememberedLiveSnapshot() {
    try {
        return JSON.parse(sessionStorage.getItem('airflowLiveSnapshot') || 'null');
    } catch (error) {
        return null;
    }
}

function getEventEntityType(event) {
    if (!event) return null;
    if (event.entityType) return event.entityType;
    return event.relatedFlightId === 'PARKING' ? 'parking' : 'flight';
}

function getEventEntityId(event) {
    if (!event) return null;
    if (event.entityId) return event.entityId;
    return event.relatedFlightId || null;
}

function isSameEventEntity(leftEvent, rightEvent) {
    return (
        getEventEntityType(leftEvent) === getEventEntityType(rightEvent)
        && getEventEntityId(leftEvent) === getEventEntityId(rightEvent)
    );
}

function cacheLiveSnapshot(flightsData, parkingData) {
    const flights = flightsData?.flights || [];
    const summary = flightsData?.summary || null;
    const events = buildHorizonEvents(flights, parkingData);
    const snapshot = {
        flights,
        parking: parkingData || null,
        summary,
        events,
        cachedAt: Date.now(),
    };

    rememberLiveSnapshot(snapshot);
    rememberHorizonEvents(events);

    const selectedEvent = loadSelectedHorizonEvent();
    if (selectedEvent) {
        const refreshedSelected = events.find((event) => isSameEventEntity(event, selectedEvent));
        if (refreshedSelected) {
            rememberSelectedHorizonEvent(refreshedSelected);
        }
    }

    return snapshot;
}

async function refreshRememberedLiveState() {
    const [flightsData, parkingData] = await Promise.all([
        fetchLiveJson('/api/flights?limit=24'),
        fetchLiveJson('/api/parking_status'),
    ]);
    const snapshot = cacheLiveSnapshot(flightsData, parkingData);
    applyHeaderSummary(snapshot.summary);
    return snapshot;
}

function navigateToEventDetail(event, index = 0) {
    rememberSelectedHorizonEvent(event);

    if (event?.detailUrl) {
        window.location.href = event.detailUrl;
        return;
    }

    if (event?.relatedFlightId === 'PARKING') {
        window.location.href = '/parking';
        return;
    }

    if (event?.relatedFlightId) {
        window.location.href = `/flight/${event.relatedFlightId}`;
        return;
    }

    window.location.href = `/event/${index}`;
}

function refreshActiveLivePage() {
    if (document.getElementById('hotspots-container') && typeof hydrateDashboardFromRememberedSnapshot === 'function') {
        hydrateDashboardFromRememberedSnapshot();
    }
    if (document.getElementById('horizon-event-timeline') && typeof hydrateHorizonFromRememberedSnapshot === 'function') {
        hydrateHorizonFromRememberedSnapshot();
    }
    if (document.getElementById('detail-flight-id') && typeof initFlightDetailDbPage === 'function') {
        initFlightDetailDbPage();
    }
    if (document.getElementById('event-detail-title') && typeof initEventDetailLivePage === 'function') {
        initEventDetailLivePage();
    }
    if (document.getElementById('parking-badge') && typeof initParkingDetailLivePage === 'function') {
        initParkingDetailLivePage();
    }
    if (document.getElementById('horizon-event-timeline') && typeof loadHorizonLiveData === 'function') {
        loadHorizonLiveData();
    }
    if (document.getElementById('hotspots-container') && typeof loadDashboardLiveData === 'function') {
        loadDashboardLiveData();
    }
    if (document.getElementById('all-flights-table-body') && typeof initFlightsLivePage === 'function') {
        initFlightsLivePage();
    }
    if ((document.getElementById('impact-before-delayed') || document.getElementById('horizon-before-delayed')) && typeof loadImpactLiveMetrics === 'function') {
        loadImpactLiveMetrics();
    }
    if (document.getElementById('audit-list') && typeof initAuditLivePage === 'function') {
        initAuditLivePage();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    refreshShellMetrics();
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    setInterval(refreshShellMetrics, 30000);
});

window.addEventListener('pageshow', (event) => {
    if (!event.persisted) return;
    refreshShellMetrics();
    refreshActiveLivePage();
});
