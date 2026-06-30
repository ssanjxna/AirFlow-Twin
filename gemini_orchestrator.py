# ============================================================
# AIRFLOW TWIN - LAYER 3: GEMINI AI ORCHESTRATOR
# ============================================================

import os
import json
import re
from dotenv import load_dotenv
import google.generativeai as genai


load_dotenv()


def risk_level_from_percent(percent):
    percent = float(percent)

    if percent >= 75:
        return "Critical"
    elif percent >= 50:
        return "High"
    elif percent >= 25:
        return "Medium"
    return "Low"


def extract_json(text):
    if not text:
        raise ValueError("Gemini returned an empty response.")

    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)

    if match:
        return json.loads(match.group(0))

    print("\nRAW GEMINI RESPONSE:")
    print(text)

    raise ValueError("Gemini response did not contain valid JSON.")


def build_gemini_prompt(airport_state):
    flight_id = airport_state.get("flight_id", "UNKNOWN")

    return f"""
You are AirFlow Twin's Airport Operations AI.

Your role is to analyze specialist risk outputs and recommend operational actions.

IMPORTANT:
- Do NOT recalculate risk.
- Use the provided risk_percent values.
- Return ONLY valid JSON.
- No markdown.
- No explanations.
- No comments.
- No trailing commas.

AIRPORT_STATE:
{json.dumps(airport_state, indent=2)}

Rules:
- Prioritize the highest risk_percent values.
- Produce a maximum of 3 root causes.
- Produce a maximum of 3 recommended actions.
- Produce a maximum of 3 checklist items.
- Recommend realistic airport operations actions only.
- Every action must include a target_team.
- Always set human_approval_required=true.
- Never invent gates, crews, staff IDs, or equipment IDs.
- If suggesting reassignment, say "check available resource first".
- Keep all reasons and summaries under 20 words.
- Return VALID JSON ONLY.

Return this exact structure:

{{
  "flight_id": "{flight_id}",
  "overall_priority": "Critical",
  "executive_summary": "...",

  "root_causes": [
    {{
      "source": "...",
      "risk_percent": 0,
      "risk_level": "...",
      "reason": "..."
    }}
  ],

  "recommended_actions": [
    {{
      "action": "...",
      "target_team": "...",
      "priority": "...",
      "expected_delay_reduction_minutes": 0,
      "validation_required": true
    }}
  ],

  "expected_impact": {{
    "current_overall_risk_percent": 0,
    "estimated_risk_after_actions_percent": 0,
    "estimated_delay_reduction_minutes": 0
  }},

  "operator_checklist": [
    {{
      "task": "...",
      "completed": false
    }}
  ],

  "human_approval_required": true
}}
"""


def fallback_recommendation(airport_state):
    specialist_outputs = airport_state.get("specialist_outputs", {})
    overall = airport_state.get("overall_risk", {})

    ranked = sorted(
        specialist_outputs.items(),
        key=lambda x: x[1].get("risk_percent", 0),
        reverse=True
    )

    root_causes = []
    actions = []
    checklist = []

    action_map = {
        "gate_events": {
            "team": "Gate Operations",
            "action": "Check available alternate gate and resolve gate conflict before boarding.",
            "minutes": 12
        },
        "delay": {
            "team": "Duty Manager",
            "action": "Start proactive delay mitigation and coordinate turnaround teams.",
            "minutes": 10
        },
        "passenger_flow": {
            "team": "Passenger Services",
            "action": "Open additional passenger processing lanes and prioritize boarding flow.",
            "minutes": 8
        },
        "baggage": {
            "team": "Baggage Operations",
            "action": "Assign extra baggage handling support to the affected flight.",
            "minutes": 6
        },
        "maintenance": {
            "team": "Maintenance",
            "action": "Review maintenance impact and confirm aircraft release readiness.",
            "minutes": 8
        },
        "security": {
            "team": "Security",
            "action": "Open additional security lane capacity during the current peak.",
            "minutes": 7
        },
        "staffing": {
            "team": "Duty Manager",
            "action": "Check available staff and reallocate resources to the highest-risk area.",
            "minutes": 6
        },
        "retail": {
            "team": "Retail Operations",
            "action": "Trigger passenger announcement to move passengers from retail areas to gate.",
            "minutes": 4
        }
    }

    for source, data in ranked[:3]:
        risk_percent = data.get("risk_percent", 0)
        risk_level = data.get("risk_level", risk_level_from_percent(risk_percent))

        root_causes.append({
            "source": source,
            "risk_percent": risk_percent,
            "risk_level": risk_level,
            "reason": f"{source} is one of the highest operational risk contributors."
        })

        mapped = action_map.get(source, action_map["delay"])

        actions.append({
            "action": mapped["action"],
            "target_team": mapped["team"],
            "priority": risk_level,
            "expected_delay_reduction_minutes": mapped["minutes"],
            "validation_required": True
        })

        checklist.append({
            "task": mapped["action"],
            "completed": False
        })

    current_risk = float(overall.get("risk_percent", 0))
    estimated_reduction = sum(a["expected_delay_reduction_minutes"] for a in actions)
    estimated_after = max(current_risk - 20, 0)

    return {
        "flight_id": airport_state.get("flight_id", "UNKNOWN"),
        "overall_priority": overall.get("risk_level", risk_level_from_percent(current_risk)),
        "executive_summary": "High operational risk detected; immediate coordinated mitigation is recommended.",
        "root_causes": root_causes,
        "recommended_actions": actions,
        "expected_impact": {
            "current_overall_risk_percent": round(current_risk, 2),
            "estimated_risk_after_actions_percent": round(estimated_after, 2),
            "estimated_delay_reduction_minutes": int(estimated_reduction)
        },
        "operator_checklist": checklist,
        "human_approval_required": True
    }


def validate_recommendation_schema(data, airport_state):
    required_keys = [
        "flight_id",
        "overall_priority",
        "executive_summary",
        "root_causes",
        "recommended_actions",
        "expected_impact",
        "operator_checklist",
        "human_approval_required"
    ]

    for key in required_keys:
        if key not in data:
            return fallback_recommendation(airport_state)

    return data


def get_gemini_recommendation(airport_state, api_key=None):
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("\nMissing GEMINI_API_KEY. Using fallback recommendation.")
        return fallback_recommendation(airport_state)

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = build_gemini_prompt(airport_state)

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.0,
                "max_output_tokens": 4000,
            }
        )

        raw_text = response.text.strip()

        recommendation = extract_json(raw_text)

        return validate_recommendation_schema(
            recommendation,
            airport_state
        )

    except Exception as error:
        print("\nGemini failed. Using fallback recommendation.")
        print("Error:", error)

        return fallback_recommendation(airport_state)
