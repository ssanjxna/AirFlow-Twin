import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib
import os

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

# read the csv file
df = pd.read_csv(file_path, header=None, names=column_names)
print(f"loaded {len(df)} flights.")

# create the target variable: 1 if delayed more than 15 minutes, 0 otherwise
# we use column 14 which is 'delay_minutes'
target_column = 'delay_minutes'
df['is_delayed'] = (df[target_column] > 15).astype(int)

# select the features we want the ai to learn from
feature_cols = ['origin', 'destination', 'airline_code', 'distance', 'time_of_day', 'day_of_week']

# remove any rows that have missing data in our chosen columns
df = df.dropna(subset=feature_cols + [target_column])

# convert text columns into numbers so the ai model can understand them
le_dict = {}
x_data = df[feature_cols].copy()

for col in feature_cols:
    le = LabelEncoder()
    x_data[col] = le.fit_transform(x_data[col].astype(str))
    le_dict[col] = le

y_data = df['is_delayed']

print("training xgboost model...")
# split data into training and testing sets
x_train, x_test, y_train, y_test = train_test_split(x_data, y_data, test_size=0.2, random_state=42)

# initialize and train the model
model = XGBClassifier(n_estimators=100, learning_rate=0.1, random_state=42)
model.fit(x_train, y_train)

# check how accurate the model is
accuracy = model.score(x_test, y_test)
print(f"model trained. accuracy: {accuracy * 100:.2f}%")

# save the trained model and the text encoders to the models folder
os.makedirs('models', exist_ok=True)
joblib.dump(model, 'models/delay_predictor.pkl')
joblib.dump(le_dict, 'models/label_encoders.pkl')

print("saved to models/delay_predictor.pkl and models/label_encoders.pkl")
print("training complete. you can now run app.py")