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

async function refreshShellMetrics() {
    try {
        const response = await fetch('/api/flights');
        const data = await response.json();
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
            time: '+10m',
            minutesAhead: 10,
            text: 'Parking congestion building near terminal access',
            type: parkingData.status,
            risk: Math.round(parkingData.congestion_score || 0),
            relatedFlightId: 'PARKING',
            impact: parkingData.cause || 'Arrival traffic is creating parking pressure.',
            recommendations: buildParkingRecommendationCards(parkingData.recommendations, Math.round(parkingData.congestion_score || 0)),
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

document.addEventListener('DOMContentLoaded', () => {
    refreshShellMetrics();
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
    setInterval(refreshShellMetrics, 30000);
});
