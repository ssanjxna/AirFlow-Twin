// ============================================================================
// DATA & CONFIGURATION
// ============================================================================

const hotspotPositions = {
    'UK-633': { x: 30, y: 12 },
    'KL-7243': { x: 43, y: 16 },
    'BA-6017': { x: 58, y: 21 },
    'SG-1280': { x: 73, y: 30 },
    'BA-7303': { x: 89, y: 42 },
    'PARKING': { x: 26, y: 71 }
};


const recommendationsDB = {
    'SG-1280': [
        { id: 'rec1', text: 'Reassign maintenance crew from KL-7243', impact: '-15m delay, -20% risk', riskReduction: 20, delayReduction: 15 },
        { id: 'rec2', text: 'Open Overflow Parking P3', impact: '-8m delay, -10% risk', riskReduction: 10, delayReduction: 8 }
    ],
    'PARKING': [
        { id: 'rec1', text: 'Open overflow parking P3 and P4', impact: '-30% congestion', riskReduction: 30, delayReduction: 15 },
        { id: 'rec2', text: 'Activate dynamic signage', impact: '-20% congestion', riskReduction: 20, delayReduction: 10 }
    ],
    'default': [
        { id: 'rec1', text: 'Reassign maintenance crew', impact: '-12m delay, -15% risk', riskReduction: 15, delayReduction: 12 },
        { id: 'rec2', text: 'Open overflow parking', impact: '-8m delay, -10% risk', riskReduction: 10, delayReduction: 8 }
    ]
};

let currentTimeStep = 0;