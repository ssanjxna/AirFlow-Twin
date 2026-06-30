import json

from backend.audit_logger import (
    init_audit_db,
    log_ai_recommendation,
    update_human_decision,
    get_audit_record
)

# Example outputs from Layer 2 and Layer 3
airport_state = {
    "flight_id": "SQ-803",
    "overall_risk": {
        "risk_percent": 74.24,
        "risk_level": "High"
    }
}

gemini_recommendation = {
    "flight_id": "SQ-803",
    "overall_priority": "Critical",
    "recommended_actions": [
        {
            "action": "Check available alternate gate and resolve gate conflict before boarding.",
            "target_team": "Gate Operations",
            "priority": "Critical",
            "validation_required": True
        },
        {
            "action": "Open additional passenger processing lanes.",
            "target_team": "Passenger Services",
            "priority": "High",
            "validation_required": True
        }
    ],
    "human_approval_required": True
}

init_audit_db()

audit_id = log_ai_recommendation(
    flight_id="SQ-803",
    airport_state=airport_state,
    gemini_recommendation=gemini_recommendation
)

print("Created audit record:", audit_id)

approved_actions = [
    gemini_recommendation["recommended_actions"][0]
]

rejected_actions = [
    gemini_recommendation["recommended_actions"][1]
]

update_human_decision(
    audit_id=audit_id,
    operator_id="operator_001",
    operator_decision="PARTIALLY_APPROVED",
    operator_notes="Gate action approved. Passenger lane action delayed due to staffing limits.",
    approved_actions=approved_actions,
    rejected_actions=rejected_actions
)

record = get_audit_record(audit_id)

print(json.dumps(record, indent=2))