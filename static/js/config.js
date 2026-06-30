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

const futureScenarios = {
    0: { 
        events: [], 
        message: "Current state: Normal operations.", 
        modifiers: {}, 
        newFlights: [] 
    },
    30: {
        events: [
            { 
                time: '+15m', 
                text: '⚠️ Maintenance Crew Shift Change', 
                type: 'warning', 
                risk: 75, 
                relatedFlightId: 'SG-1280', 
                impact: 'Crew 2 leaving. SG-1280 maintenance incomplete.', 
                recommendations: [
                    { id: 'r1', text: 'Delay Crew 2 departure', impact: '-20m delay', riskReduction: 25, delayReduction: 20 }
                ] 
            },
            { 
                time: '+25m', 
                text: '✈️ New Arrival: EK-9988 (A380)', 
                type: 'critical', 
                risk: 85, 
                relatedFlightId: 'EK-9988', 
                impact: 'Large aircraft arriving. Limited ground crew.', 
                recommendations: [
                    { id: 'r1', text: 'Pre-assign Crew B', impact: '-20m delay', riskReduction: 25, delayReduction: 20 }
                ] 
            }
        ],
        message: "Risk increasing due to crew shift change.",
        modifiers: { 
            'BA-6017': { risk: 75, delay: 35 }, 
            'SG-1280': { risk: 85, delay: 45 } 
        },
        newFlights: [
            { id: 'EK-9988', origin: 'DXB', destination: 'LHR', risk: 85, delay: 45 }
        ]
    }
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