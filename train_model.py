import os
from datetime import UTC, datetime

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

print("starting ai training...")

file_path = 'data/flights.csv'
if not os.path.exists(file_path):
    print(f"error: {file_path} not found. check your data folder.")
    exit()

# assign names to the columns based on the data snippet you provided
# if your csv already has a header row, you can remove header=None and names=column_names
column_names = [
    'flight_id', 'airline_name', 'airline_code', 'origin', 'destination', 
    'sched_dep_time', 'actual_dep_time', 'sched_arr_time', 'actual_arr_time', 
    'aircraft_type', 'registration', 'sched_duration', 'actual_duration', 
    'status', 'delay_minutes', 'delay_reason', 'terminal', 'gate', 'diverted', 
    'distance', 'col_20', 'col_21', 'delay_category', 'col_23', 'col_24', 'col_25', 
    'time_of_day', 'day_of_week', 'col_28', 'col_29', 'col_30', 'col_31'
]


def load_training_dataframe(csv_path, columns):
    with open(csv_path, "r", encoding="utf-8") as handle:
        first_row = handle.readline().strip().split(",")

    numeric_header = [str(index) for index in range(len(first_row))]

    if first_row == numeric_header:
        dataframe = pd.read_csv(csv_path)
        if len(dataframe.columns) != len(columns):
            raise ValueError(
                f"Expected {len(columns)} columns in {csv_path}, found {len(dataframe.columns)}."
            )
        dataframe.columns = columns
        return dataframe

    return pd.read_csv(csv_path, header=None, names=columns)


df = load_training_dataframe(file_path, column_names)
print(f"loaded {len(df)} flights.")

target_column = 'delay_minutes'
df[target_column] = pd.to_numeric(df[target_column], errors='coerce')
df['is_delayed'] = (df[target_column] > 15).astype(int)

for column in ['sched_dep_time', 'sched_arr_time']:
    df[column] = pd.to_datetime(df[column], format='%Y-%m-%d %H:%M:%S', errors='coerce')

df['route'] = df['origin'].astype(str) + '-' + df['destination'].astype(str)
df['is_international'] = (df['origin'].astype(str) != df['destination'].astype(str)).astype(int)
df['passenger_count'] = df['aircraft_type'].astype(str).map({
    'A320': 180,
    'A350': 300,
    'B737': 176,
    'B777': 320,
    'B787': 290,
}).fillna(180).astype(int)
df['maintenance_required'] = df['delay_reason'].astype(str).str.contains('maint', case=False, na=False).astype(int)
df['fuel_level'] = 75
df['baggage_count'] = (df['passenger_count'] * 0.7).astype(int)
df['load_factor'] = 0.82
df['is_weekend'] = df['day_of_week'].astype(str).str.lower().str.startswith(('sat', 'sun')).astype(int)
df['season'] = df['sched_dep_time'].dt.month.map({
    12: 'Winter', 1: 'Winter', 2: 'Winter',
    3: 'Spring', 4: 'Spring', 5: 'Spring',
    6: 'Summer', 7: 'Summer', 8: 'Summer',
    9: 'Autumn', 10: 'Autumn', 11: 'Autumn',
}).fillna('Summer')
df['flight_type'] = 'Passenger'
df['departure_hour'] = df['sched_dep_time'].dt.hour.fillna(10).astype(int)
df['departure_month'] = df['sched_dep_time'].dt.month.fillna(datetime.now(UTC).month).astype(int)
df['departure_day'] = df['sched_dep_time'].dt.day.fillna(datetime.now(UTC).day).astype(int)
df['arrival_hour'] = df['sched_arr_time'].dt.hour.fillna((df['departure_hour'] + 2) % 24).astype(int)
df['is_peak_hour'] = df['departure_hour'].isin([7, 8, 9, 17, 18, 19]).astype(int)
df['distance'] = pd.to_numeric(df['distance'], errors='coerce').fillna(1000).astype(int)
df['scheduled_duration'] = pd.to_numeric(df['sched_duration'], errors='coerce').fillna(120).astype(int)

feature_cols = [
    'airline_code', 'origin', 'destination', 'route', 'aircraft_type',
    'terminal', 'gate', 'is_international', 'distance', 'passenger_count',
    'maintenance_required', 'fuel_level', 'baggage_count', 'load_factor',
    'time_of_day', 'day_of_week', 'is_weekend', 'season', 'flight_type',
    'departure_hour', 'departure_month', 'departure_day', 'arrival_hour',
    'is_peak_hour', 'scheduled_duration'
]

df = df.dropna(subset=feature_cols + [target_column])

x_data = df[feature_cols].copy()
y_data = df['is_delayed']

print("training delay prediction model...")
x_train, x_test, y_train, y_test = train_test_split(
    x_data,
    y_data,
    test_size=0.2,
    random_state=42,
    stratify=y_data if y_data.nunique() > 1 else None,
)

categorical_features = [
    'airline_code', 'origin', 'destination', 'route', 'aircraft_type',
    'terminal', 'gate', 'time_of_day', 'day_of_week', 'season', 'flight_type'
]
numeric_features = [column for column in feature_cols if column not in categorical_features]

preprocessor = ColumnTransformer(
    transformers=[
        ('categorical', OneHotEncoder(handle_unknown='ignore'), categorical_features),
        ('numeric', 'passthrough', numeric_features),
    ]
)

model = LogisticRegression(
    max_iter=1000,
    solver='liblinear',
    class_weight='balanced',
    random_state=42,
)
pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('model', model),
])
pipeline.fit(x_train, y_train)

accuracy = accuracy_score(y_test, pipeline.predict(x_test))
print(f"model trained. accuracy: {accuracy * 100:.2f}%")

os.makedirs('models', exist_ok=True)
artifact = {
    'artifact_type': 'airflow_delay_predictor',
    'created_at': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
    'model_version': 'airflow_delay_predictor_v1',
    'pipeline': pipeline,
    'feature_columns': feature_cols,
    'categorical_features': categorical_features,
    'numeric_features': numeric_features,
    'metrics': {
        'accuracy': round(float(accuracy), 4),
    },
    'important_note': 'Operational flight-delay prediction only.',
}
joblib.dump(artifact, 'models/airflow_delay_predictor_artifact.pkl')

print("saved to models/airflow_delay_predictor_artifact.pkl")
print("training complete. you can now run app.py")
