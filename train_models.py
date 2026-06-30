"""
Train and save all ML models for AirFlow Twin
"""
import pandas as pd
import numpy as np
import pickle
import os
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

print("="*60)
print("🤖 AIRFLOW TWIN - MODEL TRAINING SCRIPT")
print("="*60)

os.makedirs('models', exist_ok=True)

# ============================================================================
# 1. DELAY PREDICTOR MODEL
# ============================================================================
print("\n[1/8] Training Delay Predictor Model...")
np.random.seed(42)
n_samples = 5000

df_delay = pd.DataFrame({
    'origin': np.random.choice(['DEL', 'BOM', 'BLR', 'MAA', 'HYD'], n_samples),
    'destination': np.random.choice(['SIN', 'DXB', 'LHR', 'JFK', 'HKG'], n_samples),
    'airline_code': np.random.choice(['UK', 'AI', '6E', 'SG', 'BA'], n_samples),
    'distance': np.random.randint(500, 8000, n_samples),
    'time_of_day': np.random.choice(['Morning', 'Afternoon', 'Evening', 'Night'], n_samples),
    'day_of_week': np.random.choice(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], n_samples),
    'scheduled_departure_hour': np.random.randint(0, 24, n_samples)
})

delay_prob = (
    (df_delay['distance'] > 3000).astype(int) * 0.2 +
    (df_delay['scheduled_departure_hour'].isin([7, 8, 9, 17, 18, 19])).astype(int) * 0.15 +
    (df_delay['day_of_week'].isin(['Mon', 'Fri'])).astype(int) * 0.1 +
    np.random.random(n_samples) * 0.3
)
df_delay['delayed'] = (delay_prob > 0.5).astype(int)

label_encoders_delay = {}
feature_columns_delay = ['origin', 'destination', 'airline_code', 'distance', 'time_of_day', 'day_of_week']
for col in feature_columns_delay:
    if df_delay[col].dtype == 'object':
        le = LabelEncoder()
        df_delay[col] = le.fit_transform(df_delay[col])
        label_encoders_delay[col] = le

X_train, X_test, y_train, y_test = train_test_split(df_delay[feature_columns_delay], df_delay['delayed'], test_size=0.2, random_state=42)
delay_model = GradientBoostingClassifier(n_estimators=100, random_state=42)
delay_model.fit(X_train, y_train)
print(f"  ✓ Test Accuracy: {delay_model.score(X_test, y_test):.2%}")

with open('models/delay_predictor.pkl', 'wb') as f:
    pickle.dump({'pipeline': delay_model, 'feature_columns': feature_columns_delay, 'model_version': '1.0.0'}, f)
print("  ✓ Saved to models/delay_predictor.pkl")

# ============================================================================
# 2. CONGESTION PREDICTOR MODEL (FIXED BINS)
# ============================================================================
print("\n[2/8] Training Congestion Predictor Model...")
n_samples = 3000

df_congestion = pd.DataFrame({
    'hour': np.random.randint(0, 24, n_samples),
    'day_type': np.random.choice(['weekday', 'weekend'], n_samples),
    'weather': np.random.choice(['clear', 'rain', 'fog'], n_samples),
    'flights_arriving': np.random.randint(0, 20, n_samples),
    'occupancy_rate': np.random.randint(20, 100, n_samples),
    'is_peak_hour': np.random.randint(0, 2, n_samples)
})

congestion_score = (
    df_congestion['occupancy_rate'] * 0.4 +
    df_congestion['flights_arriving'] * 2 +
    (df_congestion['is_peak_hour'] * 20) +
    (df_congestion['weather'].map({'clear': 0, 'rain': 10, 'fog': 15}))
)

# FIX: Expanded bins to 200 to prevent NaN values, and added include_lowest=True
df_congestion['congestion_level'] = pd.cut(
    congestion_score,
    bins=[-1, 50, 80, 200], 
    labels=[0, 1, 2],
    include_lowest=True
).astype(int)

le_day = LabelEncoder()
le_weather = LabelEncoder()
df_congestion['day_type'] = le_day.fit_transform(df_congestion['day_type'])
df_congestion['weather'] = le_weather.fit_transform(df_congestion['weather'])

feature_columns_congestion = ['hour', 'day_type', 'weather', 'flights_arriving', 'occupancy_rate', 'is_peak_hour']
X_train, X_test, y_train, y_test = train_test_split(df_congestion[feature_columns_congestion], df_congestion['congestion_level'], test_size=0.2, random_state=42)
congestion_model = RandomForestClassifier(n_estimators=100, random_state=42)
congestion_model.fit(X_train, y_train)
print(f"  ✓ Test Accuracy: {congestion_model.score(X_test, y_test):.2%}")

with open('models/parking_predictor.pkl', 'wb') as f:
    pickle.dump({
        'pipeline': congestion_model, 
        'feature_columns': feature_columns_congestion, 
        'config': {'label_map': {0: 'Low', 1: 'Medium', 2: 'High'}},
        'model_version': '1.0.0'
    }, f)
print("  ✓ Saved to models/parking_predictor.pkl")

# ============================================================================
# 3. BAGGAGE RISK MODEL
# ============================================================================
print("\n[3/8] Training Baggage Risk Model...")
n_samples = 2000
df_baggage = pd.DataFrame({
    'flight_passengers': np.random.randint(50, 400, n_samples),
    'baggage_count': np.random.randint(100, 800, n_samples),
    'handling_time_minutes': np.random.randint(20, 90, n_samples),
    'staff_available': np.random.randint(2, 10, n_samples),
    'is_international': np.random.randint(0, 2, n_samples),
    'time_to_departure_minutes': np.random.randint(30, 180, n_samples)
})
baggage_risk = (
    (df_baggage['baggage_count'] / df_baggage['staff_available']) * 0.3 +
    (df_baggage['handling_time_minutes'] / df_baggage['time_to_departure_minutes']) * 100 * 0.4 +
    (df_baggage['is_international'] * 20) +
    np.random.random(n_samples) * 20
)
df_baggage['risk_score'] = np.clip(baggage_risk, 0, 100)

feature_columns_baggage = ['flight_passengers', 'baggage_count', 'handling_time_minutes', 'staff_available', 'is_international', 'time_to_departure_minutes']
X_train, X_test, y_train, y_test = train_test_split(df_baggage[feature_columns_baggage], df_baggage['risk_score'], test_size=0.2, random_state=42)
baggage_model = RandomForestRegressor(n_estimators=100, random_state=42)
baggage_model.fit(X_train, y_train)
print(f"  ✓ Test R² Score: {baggage_model.score(X_test, y_test):.2%}")
with open('models/baggage_risk.pkl', 'wb') as f:
    pickle.dump({'pipeline': baggage_model, 'feature_columns': feature_columns_baggage, 'model_version': '1.0.0'}, f)
print("  ✓ Saved to models/baggage_risk.pkl")

# ============================================================================
# 4. PASSENGER FLOW MODEL
# ============================================================================
print("\n[4/8] Training Passenger Flow Model...")
n_samples = 2500
df_flow = pd.DataFrame({
    'hour': np.random.randint(0, 24, n_samples),
    'day_type': np.random.choice(['weekday', 'weekend'], n_samples),
    'flights_departing': np.random.randint(0, 15, n_samples),
    'flights_arriving': np.random.randint(0, 15, n_samples),
    'terminal_area': np.random.choice(['A', 'B', 'C', 'D'], n_samples),
    'security_wait_time': np.random.randint(5, 45, n_samples)
})
flow_risk = (
    (df_flow['flights_departing'] + df_flow['flights_arriving']) * 3 +
    df_flow['security_wait_time'] * 0.5 +
    (df_flow['hour'].isin([7, 8, 9, 17, 18, 19])).astype(int) * 15 +
    np.random.random(n_samples) * 20
)
df_flow['flow_risk_score'] = np.clip(flow_risk, 0, 100)
le_term = LabelEncoder()
le_day2 = LabelEncoder()
df_flow['terminal_area'] = le_term.fit_transform(df_flow['terminal_area'])
df_flow['day_type'] = le_day2.fit_transform(df_flow['day_type'])

feature_columns_flow = ['hour', 'day_type', 'flights_departing', 'flights_arriving', 'terminal_area', 'security_wait_time']
X_train, X_test, y_train, y_test = train_test_split(df_flow[feature_columns_flow], df_flow['flow_risk_score'], test_size=0.2, random_state=42)
flow_model = RandomForestRegressor(n_estimators=100, random_state=42)
flow_model.fit(X_train, y_train)
print(f"  ✓ Test R² Score: {flow_model.score(X_test, y_test):.2%}")
with open('models/passenger_flow.pkl', 'wb') as f:
    pickle.dump({'pipeline': flow_model, 'feature_columns': feature_columns_flow, 'model_version': '1.0.0'}, f)
print("  ✓ Saved to models/passenger_flow.pkl")

# ============================================================================
# 5. MAINTENANCE IMPACT MODEL
# ============================================================================
print("\n[5/8] Training Maintenance Impact Model...")
n_samples = 2000
df_maint = pd.DataFrame({
    'aircraft_age_years': np.random.randint(1, 30, n_samples),
    'hours_since_last_maintenance': np.random.randint(10, 1000, n_samples),
    'maintenance_type': np.random.choice(['Routine', 'Check', 'Overhaul'], n_samples),
    'estimated_duration_hours': np.random.randint(1, 24, n_samples),
    'is_peak_season': np.random.randint(0, 2, n_samples)
})
maint_prob = (
    (df_maint['aircraft_age_years'] > 15).astype(int) * 0.2 +
    (df_maint['hours_since_last_maintenance'] > 500).astype(int) * 0.3 +
    (df_maint['maintenance_type'] == 'Overhaul').astype(int) * 0.2 +
    np.random.random(n_samples) * 0.3
)
df_maint['delay_risk'] = (maint_prob > 0.5).astype(int)
le_maint = LabelEncoder()
df_maint['maintenance_type'] = le_maint.fit_transform(df_maint['maintenance_type'])

feature_columns_maint = ['aircraft_age_years', 'hours_since_last_maintenance', 'maintenance_type', 'estimated_duration_hours', 'is_peak_season']
X_train, X_test, y_train, y_test = train_test_split(df_maint[feature_columns_maint], df_maint['delay_risk'], test_size=0.2, random_state=42)
maint_model = RandomForestClassifier(n_estimators=100, random_state=42)
maint_model.fit(X_train, y_train)
print(f"  ✓ Test Accuracy: {maint_model.score(X_test, y_test):.2%}")
with open('models/maintenance_impact.pkl', 'wb') as f:
    pickle.dump({'pipeline': maint_model, 'feature_columns': feature_columns_maint, 'model_version': '1.0.0'}, f)
print("  ✓ Saved to models/maintenance_impact.pkl")

# ============================================================================
# 6, 7, 8. DUMMY PKL FILES FOR RULE-BASED ENGINES
# (Gate Events, Security, Staff, Retail don't use ML pipelines, 
# but app.py expects the .pkl files to exist so it doesn't crash)
# ============================================================================
print("\n[6/8] Creating dummy artifacts for rule-based engines...")
dummy_artifact = {'pipeline': None, 'feature_columns': [], 'model_version': '1.0.0', 'note': 'Rule-based engine'}

with open('models/gate_events.pkl', 'wb') as f:
    pickle.dump(dummy_artifact, f)
print("  ✓ Saved to models/gate_events.pkl")

with open('models/security_congestion.pkl', 'wb') as f:
    pickle.dump(dummy_artifact, f)
print("  ✓ Saved to models/security_congestion.pkl")

with open('models/staff_resource.pkl', 'wb') as f:
    pickle.dump(dummy_artifact, f)
print("  ✓ Saved to models/staff_resource.pkl")

with open('models/retail_dwell.pkl', 'wb') as f:
    pickle.dump(dummy_artifact, f)
print("  ✓ Saved to models/retail_dwell.pkl")

print("\n" + "="*60)
print("✅ ALL MODELS TRAINED AND SAVED SUCCESSFULLY!")
print("="*60)
print("\nNext steps:")
print("  1. Run: python app.py")
print("  2. Open: http://127.0.0.1:5000")
print("="*60)