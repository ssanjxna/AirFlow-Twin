# 🛫 AirFlow Twin - AI Airport Ground Operations Digital Twin

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hackathon](https://img.shields.io/badge/Hackathon-AI%20in%20Mobility-orange.svg)]()

**Predicting flight delays before they happen using AI-powered digital twin technology**

---

## 📋 Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [AI Models](#ai-models)
- [API Endpoints](#api-endpoints)
- [Team](#team)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

AirFlow Twin is an **AI-powered digital twin platform** that transforms airport ground operations from reactive to proactive. By creating a virtual replica of airport activities and using predictive analytics, we help airports **reduce delays by up to 40%** through intelligent resource allocation and early bottleneck detection.

### 🏆 Built for: AI in Mobility Hackathon 2024

---

## ❌ Problem Statement

Airport delays cost the industry **$30+ billion annually**. The root cause isn't just aircraft issues—it's **inefficient coordination** of ground resources:

- ✗ Maintenance crews unavailable when needed
- ✗ Fuel trucks stuck in congestion
- ✗ Baggage vehicles poorly routed
- ✗ Gate conflicts causing cascading delays
- ✗ Parking overflow blocking service roads

**Current systems react AFTER problems occur.** We predict them **30 minutes in advance**.

---

## ✅ Solution

AirFlow Twin creates a **live virtual model** of airport operations that:

1. **Simulates** upcoming activities (next 30-60 minutes)
2. **Predicts** delay risks using machine learning (85%+ accuracy target)
3. **Recommends** specific actions (reassign crew, reroute trucks, etc.)
4. **Visualizes** future states to evaluate decisions before implementation

### Example Impact:
Flight: SG-1280 (DEL → KUL)
Current Risk: 80% (40min delay predicted)
AI Recommendation:
✓ Reassign maintenance crew from KL-7243
✓ Open Overflow Parking P3
✓ Pre-position fuel truck at Gate A12
Expected Result: Risk drops to 35% (12min delay)


---

## 🌟 Key Features

### 1. **Interactive Digital Twin Dashboard**
- Real-time 3D airport visualization
- Scrollable map showing aircraft, gates, and parking
- Color-coded risk indicators (Red/Orange/Green)
- Live flight status tracking

### 2. **Predictive Delay Analytics**
- Risk forecasting for next 60 minutes
- Dynamic risk bars showing trend over time
- Automatic detection of operational bottlenecks
- Weather and traffic impact analysis

### 3. **AI Decision Engine**
- Selectable recommendations with checkboxes
- Individual impact calculation per recommendation
- "Apply" button to simulate implementation
- Real-time risk score updates

### 4. **Resource Optimization**
- Maintenance crew allocation
- Fuel truck routing
- Baggage vehicle scheduling
- Gate assignment optimization
- Parking congestion prediction

### 5. **Time-Based Simulation**
- View airport state at: Now, +10m, +30m, +1h
- Event timeline with upcoming activities
- Crew shift change predictions
- Weather warnings integration

---

## 🛠 Technology Stack

### **Backend**
- **Flask 3.0** - Python web framework
- **XGBoost** - Machine learning for delay prediction
- **Google Gemini API** - AI recommendation generation
- **SQLite** - Database for operations data

### **Frontend**
- **HTML5 + Tailwind CSS** - Responsive UI
- **Vanilla JavaScript** - Interactive components
- **Chart.js** - Risk forecast visualization

### **AI/ML**
- **scikit-learn** - Data preprocessing
- **pandas/numpy** - Data manipulation
- **joblib** - Model serialization

### **Deployment**
- **Render/Heroku** - Cloud hosting
- **Gunicorn** - WSGI server

---

## 📦 Installation

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)
- Git

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/AirFlow-Twin.git
cd AirFlow-Twin

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your API keys:
# - GEMINI_API_KEY (required for AI recommendations)

# 5. Run the application
python app.py

# 6. Open browser
# Navigate to http://127.0.0.1:5000

🚀 Usage
For Airport Operators:
Monitor Current State
View live airport map with flight positions
Check risk scores for each aircraft
Review the Flight Risk List (sorted by priority)
Predict Future Conditions
Click time buttons: Now → +10m → +30m → +1h
Watch risk forecast bars animate
Review upcoming events timeline
Apply AI Recommendations
Click any aircraft on the map
Review AI recommendations in the right panel
Check boxes for actions to apply
Click "Apply Selected Recommendations"
Watch risk scores update in real-time

For Developers:
# Example: Get delay prediction
from models.delay_predictor import DelayPredictor

predictor = DelayPredictor()
risk_score = predictor.predict(
    flight_id='SG-1280',
    origin='DEL',
    destination='KUL',
    scheduled_time='14:30',
    maintenance_required=True
)
# Returns: 80 (80% delay risk)
