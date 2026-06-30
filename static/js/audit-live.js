// ============================================================================
// LIVE AUDIT PAGE
// ============================================================================

let auditLiveEntries = [];

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('audit-list')) {
        initAuditLivePage();
    }
});

async function initAuditLivePage() {
    try {
        const data = await fetchLiveJson('/api/audit_feed?limit=100');
        auditLiveEntries = data.entries || [];
        renderAuditLiveEntries(auditLiveEntries);
        if (auditLiveEntries.length) {
            renderAuditLiveDetail(auditLiveEntries[0]);
        }
    } catch (error) {
        console.error('Error loading audit feed:', error);
    }
}

function renderAuditLiveEntries(entries) {
    const list = document.getElementById('audit-list');
    const empty = document.getElementById('audit-empty-state');
    const count = document.getElementById('audit-entry-count');
    if (!list || !empty || !count) return;

    list.innerHTML = '';
    count.textContent = `${entries.length} entr${entries.length === 1 ? 'y' : 'ies'}`;

    if (!entries.length) {
        empty.classList.remove('hidden');
        return;
    }

    empty.classList.add('hidden');
    entries.forEach((entry, index) => {
        const secondaryText = `${entry.secondary_label}: ${entry.before_secondary_percent}% -> ${entry.after_secondary_percent}%`;
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'w-full text-left bg-slate-800/50 border border-slate-700 rounded-lg p-4 hover:bg-slate-800 transition';
        card.onclick = () => renderAuditLiveDetail(entry, index);
        card.innerHTML = `
            <div class="flex items-start justify-between gap-3">
                <div>
                    <p class="text-sm font-bold text-white">${entry.entity_id || entry.flight_id}</p>
                    <p class="text-xs text-slate-500 mt-1">${new Date(entry.timestamp).toLocaleString()}</p>
                </div>
                <span class="text-xs px-2 py-1 rounded ${getPriorityClass(entry.after_risk_percent)}">${Math.round(entry.after_risk_percent)}% risk</span>
            </div>
            <p class="text-sm text-slate-300 mt-3">${entry.actions.join(' | ')}</p>
            <div class="flex items-center justify-between mt-3 text-xs text-slate-400">
                <span>Delay saved: ${entry.total_delay_saved}m</span>
                <span>${secondaryText}</span>
            </div>
        `;
        list.appendChild(card);
    });
}

function renderAuditLiveDetail(entry) {
    const detail = document.getElementById('audit-detail');
    const empty = document.getElementById('audit-detail-empty');
    if (!detail || !empty) return;

    empty.classList.add('hidden');
    detail.classList.remove('hidden');
    document.getElementById('audit-detail-flight').textContent = entry.entity_id || entry.flight_id;
    document.getElementById('audit-detail-operator').textContent = entry.operator_id;
    document.getElementById('audit-detail-time').textContent = new Date(entry.timestamp).toLocaleString();
    document.getElementById('audit-detail-risk-before').textContent = `${Math.round(entry.before_risk_percent)}%`;
    document.getElementById('audit-detail-risk-after').textContent = `${Math.round(entry.after_risk_percent)}%`;
    document.getElementById('audit-detail-secondary-label').textContent = entry.secondary_label || 'Confidence';
    document.getElementById('audit-detail-secondary-before').textContent = `${entry.before_secondary_percent}%`;
    document.getElementById('audit-detail-secondary-after').textContent = `${entry.after_secondary_percent}%`;
    document.getElementById('audit-detail-delay-before').textContent = `${entry.before_delay_minutes}m`;
    document.getElementById('audit-detail-delay-after').textContent = `${entry.after_delay_minutes}m`;
    document.getElementById('audit-detail-delay-saved').textContent = `${entry.total_delay_saved}m`;

    const actions = document.getElementById('audit-detail-actions');
    actions.innerHTML = '';
    entry.actions.forEach((actionText) => {
        const item = document.createElement('li');
        item.className = 'border border-slate-700 rounded p-2 bg-slate-900/40';
        item.textContent = actionText;
        actions.appendChild(item);
    });
}
