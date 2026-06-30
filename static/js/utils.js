// ============================================================================
// UTILITY FUNCTIONS (Shared across all pages)
// ============================================================================

function getRiskClass(risk) { 
    if (risk >= 80) return 'high-risk'; 
    if (risk >= 50) return 'medium-risk'; 
    return 'low-risk'; 
}

function getRiskColor(risk) { 
    if (risk >= 80) return 'text-red-500'; 
    if (risk >= 50) return 'text-orange-500'; 
    return 'text-green-500'; 
}

function getRiskBg(risk) { 
    if (risk >= 80) return 'bg-red-500'; 
    if (risk >= 50) return 'bg-orange-500'; 
    return 'bg-green-500'; 
}

function getPriorityLabel(risk) { 
    if (risk >= 80) return 'CRITICAL'; 
    if (risk >= 50) return 'HIGH'; 
    return 'NORMAL'; 
}

function getPriorityClass(risk) { 
    if (risk >= 80) return 'bg-red-500/20 text-red-400 border-red-500/30'; 
    if (risk >= 50) return 'bg-orange-500/20 text-orange-400 border-orange-500/30'; 
    return 'bg-green-500/20 text-green-400 border-green-500/30'; 
}

function getBadgeClass(risk) { 
    if (risk >= 80) return 'bg-red-600'; 
    if (risk >= 50) return 'bg-orange-600'; 
    return 'bg-green-600'; 
}

function updateCurrentTime() { 
    const el = document.getElementById('current-time');
    if(el) el.textContent = new Date().toTimeString().split(' ')[0]; 
}

function updateHighRiskCount(flights) { 
    const el = document.getElementById('high-risk-count');
    if(el) el.textContent = flights.filter(f => f.risk >= 80).length; 
}

function toggleAIImpact() { 
    const modal = document.getElementById('ai-impact-modal'); 
    const backdrop = document.getElementById('modal-backdrop'); 
    if (modal && backdrop) {
        if (modal.classList.contains('active')) { 
            modal.classList.remove('active'); 
            backdrop.classList.remove('active'); 
        } else { 
            modal.classList.add('active'); 
            backdrop.classList.add('active'); 
        }
    }
}