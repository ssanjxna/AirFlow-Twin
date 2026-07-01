# AirFlow Twin

AirFlow Twin is an airport ground-operations digital twin built for AutoForge Hackathon 2026. It combines a live operations dashboard, flight-delay risk scoring, parking-congestion prediction, AI-assisted recommendations, action tracking, and audit visibility so operators can move from reactive firefighting to proactive intervention.

The current build is a working demo platform, not just a concept deck. It already includes a Flask web app, SQLite persistence, simulator-driven flight injection, model artifacts, live operational pages, apply-action workflows, impact summaries, and automated tests.

## Project Snapshot

| Area | Status | Notes |
| --- | --- | --- |
| Live simulator dashboard | Done | Top-risk flight hotspots, parking hotspot, live summary metrics, future-event preview |
| Flight risk analysis page | Done | Delay risk, confidence, risk cause, AI recommendations, apply actions |
| Parking congestion analysis | Done | Predicted congestion, occupancy, cause analysis, apply actions |
| Prediction horizon page | Done | Future event timeline and horizon risk bars |
| Event detail page | Done | Opens from horizon events and resolves to live flight or parking data |
| Flights management page | Done | Sortable live flight list with risk and delay information |
| AI impact page | Done | Before/after metrics, saved delay, heuristic business-value KPIs |
| Audit page | Done | Database-backed history of applied actions with before/after comparisons |
| Simulator ingestion API | Done | Accepts new flights and persists them into the live demo |
| SQLite operational persistence | Done | Recommendation state, executions, impact summary, audit logs |
| Gemini recommendation orchestration | Done with fallback | Uses Gemini when `GEMINI_API_KEY` is present, otherwise falls back to deterministic recommendations |
| Specialist model artifact library | Done | Delay, parking, maintenance, passenger flow, baggage, gate, security, staffing, retail artifacts are present |
| Full multi-specialist runtime wiring in main Flask flow | Partial | Delay and parking are live; broader specialist artifacts are available in backend utilities and repo assets |
| Automated test coverage | Done | `pytest` passed: 11 tests on July 1, 2026 |

## What Is Already Implemented

- A live dashboard at `/` that shows the most critical flight hotspots and parking pressure on the airport map.
- A flight-level decision page at `/flight/<flight_id>` with risk scoring, predicted delay, cause summary, recommendation cards, and apply-action behavior.
- A parking decision page at `/parking` with congestion scoring, occupancy estimates, recommendation cards, and persistent action execution.
- A prediction horizon page at `/horizon` that turns live risks into upcoming operational events.
- An event detail page at `/event/<event_index>` that can resolve to either flight or parking actions.
- An AI impact page at `/ai-impact` that summarizes before-vs-after outcomes once recommendations are applied.
- An audit page at `/audit` that shows what actions were applied, by whom, and what changed.
- A calibration page at `/calibrate` for mapping parking zones and flight markers onto the background airport image.
- A simulator script in [simulator.py](/K:/AutoForge%20Hackathon%202026/AirFlow-Twin/simulator.py) that injects LOW, MEDIUM, HIGH, and CRITICAL scenarios into the live system.
- Database-backed operational state in [database/operational_state.py](/K:/AutoForge%20Hackathon%202026/AirFlow-Twin/database/operational_state.py) for recommendation persistence, impact calculations, and audit feeds.
- Model artifacts in `models/` and loader adapters in `loaders/` for a broader specialist-model architecture.

## Architecture

### End-to-End Runtime Flow

1. Synthetic CSV datasets and SQLite records provide the baseline airport operating picture.
2. [utils/data_loader.py](/K:/AutoForge%20Hackathon%202026/AirFlow-Twin/utils/data_loader.py) merges seeded data with any simulator-inserted flights already persisted in SQLite.
3. The Flask app enriches flights with delay-risk predictions and predicted delay minutes.
4. Parking status is scored separately through the parking congestion model.
5. The app builds an airport-state view and passes it to the recommendation layer.
6. Gemini generates recommendation JSON when configured; otherwise the system uses a deterministic fallback.
7. When operators apply actions, the system updates persisted risk, predicted delay, impact metrics, and audit history.
8. Live pages refresh from API endpoints and shared browser-side cached state.

### Tech Stack

| Layer | Technologies |
| --- | --- |
| Web app | Flask 3.0, Flask-SocketIO |
| Alternate API stub | FastAPI |
| Frontend | HTML, Tailwind via CDN, vanilla JavaScript, sessionStorage-backed shared live state |
| Database | SQLite |
| Data/ML | pandas, numpy, scikit-learn, XGBoost, joblib |
| AI recommendations | Google Gemini (`gemini-2.5-flash`) with local fallback logic |
| Testing | pytest |

### Current UI and API Surface

Pages:

- `/` live simulator dashboard
- `/flights` all flights view
- `/horizon` prediction horizon
- `/flight/<flight_id>` flight decision page
- `/event/<event_index>` event detail page
- `/parking` parking decision page
- `/ai-impact` impact summary page
- `/audit` audit page
- `/calibrate` map calibration tool

Key APIs:

- `GET /api/flights`
- `GET /api/flight/<flight_id>/detail`
- `POST /api/flight/<flight_id>/apply_recommendations`
- `POST /api/simulator/add-flight`
- `GET /api/parking_status`
- `POST /api/parking/apply_recommendations`
- `GET /api/impact_summary`
- `GET /api/audit_feed`

## AI Models and Decision Logic

### Live Models Used by the Flask App

| Capability | Runtime method | Status in main app | Notes |
| --- | --- | --- | --- |
| Flight delay risk | Logistic Regression artifact | Live | Loaded from `models/airflow_delay_predictor_artifact.pkl` |
| Parking congestion | RandomForest classifier artifact | Live | Loaded through `ParkingCongestionPredictor` |
| Flight recommendations | Gemini plus fallback JSON schema | Live | Requires `GEMINI_API_KEY` for Gemini path |
| Airport-state aggregation | Weighted specialist-risk combiner | Live | Used to summarize cross-functional operational pressure |

### Specialist Model Portfolio Present in the Repo

| Capability | Method | Artifact status | Notes |
| --- | --- | --- | --- |
| Delay prediction | Logistic Regression baseline | Present and live | Created by [train_model.py](/K:/AutoForge%20Hackathon%202026/AirFlow-Twin/train_model.py) |
| Delay prediction experiment | XGBoost classifier | Present, not current runtime default | Preserved in `airflow_delay_predictor_artifact.resaved.pkl` |
| Parking congestion | RandomForest classifier | Present and live | Predicts Low/Medium/High congestion |
| Maintenance impact | RandomForest classifier | Present | Backend-ready specialist artifact |
| Passenger flow | Regressor | Present | Produces continuous 0-100 risk score |
| Baggage risk | Regressor | Present | Produces continuous 0-100 risk score |
| Gate event risk | Rule engine | Present | Detects overlaps, delays, and gate load |
| Security congestion | Rule engine | Present | Uses queue pressure and screening behavior |
| Staffing risk | Rule engine | Present | Uses shift coverage, absence, training age, and peak load |
| Retail dwell risk | Rule engine | Present | Uses transaction density and near-gate passenger behavior |

### Overall Airport-State Weighting

The airport-state builder combines specialist outputs into a single operational-risk view using these weights:

| Specialist | Weight |
| --- | --- |
| Delay | 0.25 |
| Gate events | 0.18 |
| Passenger flow | 0.15 |
| Baggage | 0.12 |
| Maintenance | 0.12 |
| Security | 0.08 |
| Staffing | 0.07 |
| Retail | 0.03 |

This weighting logic lives in [backend/airport_state_builder.py](/K:/AutoForge%20Hackathon%202026/AirFlow-Twin/backend/airport_state_builder.py).

## Model Specifications and Evaluation

### Evaluation Snapshot

| Model | Type | Feature count | Evaluation snapshot |
| --- | --- | --- | --- |
| Delay predictor (runtime default) | Logistic Regression | 25 | Accuracy: 0.565 |
| Delay predictor experiment | XGBoost classifier | 25 | Accuracy: 0.655, Precision: 0.318, Recall: 0.115, F1: 0.169, ROC-AUC: 0.472 |
| Parking congestion | RandomForest classifier | 21 | Accuracy: 0.935, Weighted Precision: 0.938, Weighted Recall: 0.935, Weighted F1: 0.935 |
| Maintenance impact | RandomForest classifier | 30 | Accuracy: 0.605, Precision: 0.407, Recall: 0.407, F1: 0.407, ROC-AUC: 0.644 |
| Passenger flow | Regressor | 22 | MAE: 0.721, RMSE: 1.270, R2: 0.994 |
| Baggage risk | Regressor | 23 | MAE: 2.333, RMSE: 3.005, R2: 0.926 |

### Important Evaluation Notes

- These metrics come from the saved model artifacts currently in `models/`.
- Several targets are synthetic or engineered, so high scores should be treated as demo-validation signals, not production-grade external benchmarks.
- The main Flask app currently uses the logistic-regression delay artifact, not the alternate XGBoost experiment.
- Rule-engine specialists for gate, security, staffing, and retail are domain-logic modules, so they do not report train/test metrics in the same way as the supervised artifacts.

## Data Footprint

The project includes synthetic airport operations datasets at useful demo scale:

| Dataset | Approximate size |
| --- | --- |
| Flights | ~1,000 rows |
| Passengers | ~2,500 rows |
| Baggage | ~2,800 rows |
| Gate events | ~1,200 rows |
| Maintenance logs | ~400 rows |
| Parking data | ~2,000 rows |
| Security screening | ~2,500 rows |
| Retail transactions | ~3,000 rows |
| Staff shifts | ~600 rows |

SQLite can also be initialized and seeded separately through [database/init_database.py](/K:/AutoForge%20Hackathon%202026/AirFlow-Twin/database/init_database.py), which resets the schema and seeds 300 flights into the demo database.

## Local Setup

### Prerequisites

- Python 3.10+
- A virtual environment
- Optional: a Gemini API key for LLM-generated recommendations

### Run the App

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python database/init_database.py
python app.py
```

Open `http://127.0.0.1:5000`.

### Optional Live Demo Ingestion

```bash
python simulator.py
```

This posts scenario flights into `POST /api/simulator/add-flight` so the dashboard and decision views change in a believable way during demos.

### Run Tests

```bash
.\venv\Scripts\python.exe -m pytest
```

Last verified locally on July 1, 2026:

- 11 tests passed
- 2 deprecation warnings from `google._upb._message`

## Honest Notes About the Current Build

- The data is synthetic and seeded for hackathon/demo use.
- The live Flask experience already works, but not every specialist artifact is fully wired into the main UI path yet.
- Delay and parking are the strongest live model integrations today.
- Impact KPIs such as cost savings and passenger satisfaction are heuristic demo metrics derived from saved delay minutes, not audited financial models.
- Gemini is optional. The app still functions without it because a local fallback recommendation engine is implemented.
- There are some legacy files in the repo from earlier UI iterations, but the active user flow is driven by `app.py`, the `templates/` pages listed above, and the `*-live.js` scripts.

## Suggested Presentation Content

This section is written so you can copy facts directly into ChatGPT or another slide-generation tool without it inventing the project status.

### 1. Team Presentation

- AirFlow Twin is a cross-functional hackathon project spanning airport operations, backend engineering, applied ML, and frontend decision-support UX.
- The work naturally breaks into four streams: live digital twin UI, data and simulator pipeline, AI/ML artifact training, and recommendation/audit workflow design.
- Replace generic role labels with actual teammate names before presenting.

### 2. Problem Statement

- Airport ground operations often become reactive: operators notice delays after gate conflicts, maintenance delays, passenger surges, or landside congestion have already cascaded.
- Separate systems make it hard to see the combined impact of flights, baggage, staff, parking, and gate activity in one place.
- The opportunity is to forecast disruption early enough to apply targeted interventions before delay minutes accumulate.

### 3. Solution Overview

- AirFlow Twin creates a digital twin of airport operations by combining live operational data, predictive models, scenario simulation, and AI-generated actions.
- Operators can inspect risky flights, understand why the risk is elevated, review recommended actions, and apply selected mitigations directly in the interface.
- The platform also tracks the effect of those actions through before/after metrics and audit logs.

### 4. Existing Model Research Conclusion

- A hybrid approach works best for this problem: supervised ML where structured labels exist, rule engines where operational logic matters, and LLM orchestration for human-readable recommendations.
- RandomForest performed strongly for parking congestion on synthetic labeled data.
- Continuous-risk regressors worked well for passenger-flow and baggage-risk scoring.
- Delay prediction remains a harder problem; the repo keeps both a simpler logistic-regression baseline and an alternate XGBoost experiment for comparison.
- Human approval remains important, so the recommendation layer is assistive rather than fully autonomous.

### 5. Architecture (Tech Stack)

- Backend: Flask, Flask-SocketIO, FastAPI stub, SQLite
- Frontend: HTML, Tailwind CSS via CDN, vanilla JavaScript
- Data/ML: pandas, numpy, scikit-learn, XGBoost, joblib
- AI orchestration: Google Gemini with deterministic fallback
- Quality: pytest-based smoke and workflow tests

### 6. AI Models Architecture

- Input sources: synthetic CSV datasets, seeded SQLite tables, and simulator-inserted flights
- Processing layer: `AirportDataLoader` merges persisted state with operational datasets
- Prediction layer: flight delay model and parking congestion model run in the main app; additional specialist artifacts are available for maintenance, passenger flow, baggage, security, staffing, gate, and retail
- Aggregation layer: airport-state builder combines specialist risks into a weighted overall risk
- Recommendation layer: Gemini or fallback engine returns actions, impact estimates, and checklist items
- Action layer: selected mitigations persist to operational tables and feed impact and audit analytics

### 7. Model Specifications and Evaluation

- Delay runtime model: Logistic Regression, 25 features, accuracy 56.5%
- Delay experiment model: XGBoost, 25 features, accuracy 65.5%, precision 31.8%, recall 11.5%, F1 16.9%, ROC-AUC 0.472
- Parking congestion: RandomForest, 21 features, accuracy 93.5%, weighted F1 93.5%
- Maintenance impact: RandomForest, 30 features, accuracy 60.5%, ROC-AUC 0.644
- Passenger flow: regressor, 22 features, MAE 0.721, RMSE 1.270, R2 0.994
- Baggage risk: regressor, 23 features, MAE 2.333, RMSE 3.005, R2 0.926
- Important caveat: these are hackathon-era metrics on synthetic or engineered data, so they should be presented honestly as prototype validation.

### 8. Business Value

- Earlier risk detection can reduce operational delay minutes before the disruption reaches passengers.
- The UI already quantifies before-vs-after delay reduction when recommendations are applied.
- The project demonstrates measurable operator value through time saved, lower predicted risk, and clearer accountability.
- The demo also estimates cost savings and passenger satisfaction uplift from saved delay minutes, which helps make the concept business-facing for judges and stakeholders.

### 9. Future Work

- Replace synthetic inputs with live airport systems, IoT, parking sensors, and airline/ground-handling feeds
- Wire the full specialist artifact stack into the main decision loop instead of relying on partial live integration
- Improve delay modeling with stronger labels, temporal features, and calibration
- Add user authentication, role-based approvals, and multi-operator collaboration
- Support multi-airport configuration and cleaner map calibration workflows
- Turn heuristic KPI formulas into finance-approved ROI models

## Prompt to Paste Into ChatGPT for Slide Generation

```text
Create a polished 9-slide hackathon presentation for a project called "AirFlow Twin".

Important constraints:
- Use only the facts provided below.
- Do not invent team names, airports, customers, or performance claims.
- Present the system as a working prototype with honest limitations.
- Keep the tone professional, confident, and hackathon-judge friendly.
- For each slide, provide:
  1. a slide title
  2. a 1-sentence headline
  3. 3 to 5 concise bullet points
  4. a suggestion for the visual on that slide

Slides to generate:
1. Team Presentation
2. Problem Statement
3. Solution Overview
4. Existing Model Research Conclusion
5. Architecture (Tech Stack)
6. AI Models Architecture
7. Model Specifications and Evaluation
8. Business Value
9. Future Work

Project facts:
- AirFlow Twin is an airport ground-operations digital twin built for AutoForge Hackathon 2026.
- It already has a working Flask web app with pages for a live dashboard, flights, prediction horizon, flight detail, event detail, parking detail, AI impact, audit log, and map calibration.
- It uses SQLite for persistence and tracks recommendation state, action execution, audit history, and impact summaries.
- The live app currently uses a flight-delay model, a parking-congestion model, AI/fallback recommendations, and persistent apply-action workflows.
- Gemini is used when an API key is available, otherwise the system falls back to deterministic recommendations.
- The repo also contains specialist artifacts for maintenance, passenger flow, baggage risk, gate-event risk, security congestion, staffing risk, and retail dwell risk.
- The airport-state builder combines specialist outputs with weights: delay 0.25, gate events 0.18, passenger flow 0.15, baggage 0.12, maintenance 0.12, security 0.08, staffing 0.07, retail 0.03.
- Synthetic demo datasets include about 1,000 flights, 2,500 passengers, 2,800 baggage records, 1,200 gate events, 400 maintenance logs, 2,000 parking rows, 2,500 security rows, 3,000 retail rows, and 600 staff-shift rows.
- Flight-delay runtime model: Logistic Regression, 25 features, accuracy 56.5%.
- Alternate delay experiment: XGBoost, 25 features, accuracy 65.5%, precision 31.8%, recall 11.5%, F1 16.9%, ROC-AUC 0.472.
- Parking congestion model: RandomForest, 21 features, accuracy 93.5%, weighted F1 93.5%.
- Maintenance impact model: RandomForest, 30 features, accuracy 60.5%, ROC-AUC 0.644.
- Passenger-flow regressor: 22 features, MAE 0.721, RMSE 1.270, R2 0.994.
- Baggage-risk regressor: 23 features, MAE 2.333, RMSE 3.005, R2 0.926.
- The system lets operators apply AI recommendations and immediately see reduced predicted delay and lower risk in the UI.
- The audit page records what action was applied, by whom, and the before/after metrics.
- The AI impact page summarizes before/after delayed flights, total delay, time saved, heuristic cost savings, and heuristic passenger satisfaction gain.
- This is a hackathon prototype using synthetic or engineered data, so model metrics should be presented honestly as prototype validation, not production certification.
```
