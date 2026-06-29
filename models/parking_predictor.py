import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib
import os

class ParkingCongestionPredictor:
    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.is_trained = False
        
    def load_data(self):
        """Load parking data from CSV"""
        try:
            df = pd.read_csv('data/parking_data.csv')
            return df
        except FileNotFoundError:
            print("Parking data not found. Generating synthetic data...")
            return self.generate_synthetic_data()
    
    def generate_synthetic_data(self):
        """Generate synthetic parking data for training"""
        np.random.seed(42)
        n_samples = 2000
        
        data = {
            'hour': np.random.randint(5, 23, n_samples),
            'day_type': np.random.choice(['weekday', 'weekend'], n_samples),
            'weather': np.random.choice(['clear', 'rain', 'snow'], n_samples, p=[0.7, 0.2, 0.1]),
            'flights_arriving': np.random.randint(0, 15, n_samples),
            'total_capacity': np.random.choice([300, 500, 800], n_samples),
            'occupied': np.random.randint(0, 800, n_samples),
        }
        
        df = pd.DataFrame(data)
        
        # Calculate congestion score (0-100)
        df['occupancy_rate'] = (df['occupied'] / df['total_capacity']) * 100
        
        # Peak hours: 7-9 AM, 5-7 PM
        df['is_peak_hour'] = df['hour'].apply(lambda x: 1 if (7 <= x <= 9) or (17 <= x <= 19) else 0)
        
        # Calculate congestion score
        df['congestion_score'] = (
            df['occupancy_rate'] * 0.5 +
            df['is_peak_hour'] * 20 +
            df['flights_arriving'] * 2 +
            np.where(df['weather'] == 'rain', 10, 0) +
            np.where(df['day_type'] == 'weekend', 5, 0) +
            np.random.randint(-5, 5, n_samples)
        )
        
        # Normalize to 0-100
        df['congestion_score'] = df['congestion_score'].clip(0, 100).round(2)
        
        # Determine status
        def get_status(score):
            if score < 30:
                return 'low'
            elif score < 60:
                return 'normal'
            elif score < 85:
                return 'high'
            else:
                return 'critical'
        
        df['status'] = df['congestion_score'].apply(get_status)
        
        # Save to CSV
        df.to_csv('data/parking_data.csv', index=False)
        print("✓ Generated synthetic parking data")
        
        return df
    
    def train(self):
        """Train the parking congestion prediction model"""
        print("Training parking congestion predictor...")
        
        df = self.load_data()
        
        # Encode categorical variables
        self.label_encoders['day_type'] = LabelEncoder()
        self.label_encoders['weather'] = LabelEncoder()
        
        df['day_type_encoded'] = self.label_encoders['day_type'].fit_transform(df['day_type'])
        df['weather_encoded'] = self.label_encoders['weather'].fit_transform(df['weather'])
        
        # Features
        X = df[['hour', 'day_type_encoded', 'weather_encoded', 'flights_arriving', 'occupancy_rate', 'is_peak_hour']]
        y = df['congestion_score']
        
        # Split and train
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        print(f"✓ Model trained!")
        print(f"  Train R²: {train_score:.3f}")
        print(f"  Test R²: {test_score:.3f}")
        
        self.is_trained = True
        
        # Save model
        self.save_model()
        
        return self
    
    def save_model(self):
        """Save trained model"""
        os.makedirs('models', exist_ok=True)
        joblib.dump(self.model, 'models/parking_predictor.pkl')
        joblib.dump(self.label_encoders, 'models/parking_encoders.pkl')
        print("✓ Model saved to models/parking_predictor.pkl")
    
    def load_model(self):
        """Load trained model"""
        try:
            self.model = joblib.load('models/parking_predictor.pkl')
            self.label_encoders = joblib.load('models/parking_encoders.pkl')
            self.is_trained = True
            print("✓ Parking predictor loaded")
            return True
        except FileNotFoundError:
            print("⚠ No trained model found. Training new model...")
            self.train()
            return True
    
    def predict(self, hour=None, day_type='weekday', weather='clear', 
                flights_arriving=5, occupancy_rate=50, is_peak_hour=0):
        """
        Predict parking congestion
        
        Parameters:
        - hour: Current hour (0-23)
        - day_type: 'weekday' or 'weekend'
        - weather: 'clear', 'rain', or 'snow'
        - flights_arriving: Number of flights arriving in next 30 min
        - occupancy_rate: Current occupancy percentage (0-100)
        - is_peak_hour: 1 if peak hour, 0 otherwise
        
        Returns:
        - Dictionary with congestion_score, status, and recommendations
        """
        if not self.is_trained:
            self.load_model()
        
        # Encode inputs
        day_type_encoded = self.label_encoders['day_type'].transform([day_type])[0]
        weather_encoded = self.label_encoders['weather'].transform([weather])[0]
        
        # Prepare input
        input_data = pd.DataFrame({
            'hour': [hour],
            'day_type_encoded': [day_type_encoded],
            'weather_encoded': [weather_encoded],
            'flights_arriving': [flights_arriving],
            'occupancy_rate': [occupancy_rate],
            'is_peak_hour': [is_peak_hour]
        })
        
        # Predict
        congestion_score = self.model.predict(input_data)[0]
        congestion_score = round(congestion_score, 2)
        
        # Determine status
        if congestion_score < 30:
            status = 'low'
            color = 'green'
        elif congestion_score < 60:
            status = 'normal'
            color = 'yellow'
        elif congestion_score < 85:
            status = 'high'
            color = 'orange'
        else:
            status = 'critical'
            color = 'red'
        
        # Generate recommendations
        recommendations = self._get_recommendations(status, congestion_score, occupancy_rate)
        
        return {
            'congestion_score': congestion_score,
            'status': status,
            'color': color,
            'occupancy_rate': round(occupancy_rate, 2),
            'recommendations': recommendations
        }
    
    def _get_recommendations(self, status, score, occupancy):
        """Generate recommendations based on congestion level"""
        recs = []
        
        if status == 'critical':
            recs = [
                "🚨 Open overflow parking P3 and P4 immediately",
                " Activate dynamic signage to redirect traffic",
                "📱 Send SMS alerts to incoming passengers",
                " Coordinate with ride-share for alternative drop-off"
            ]
        elif status == 'high':
            recs = [
                "⚠️ Prepare overflow parking P3",
                "️ Display 'Parking Full' messages on highway signs",
                "👥 Deploy staff to direct traffic"
            ]
        elif status == 'normal':
            recs = [
                "✓ Standard operations",
                "📊 Monitor occupancy levels"
            ]
        else:
            recs = [
                "✓ Parking capacity adequate",
                "😊 No action needed"
            ]
        
        return recs

# Test the model
if __name__ == "__main__":
    predictor = ParkingCongestionPredictor()
    predictor.train()
    
    # Test prediction
    result = predictor.predict(
        hour=9,
        day_type='weekday',
        weather='clear',
        flights_arriving=8,
        occupancy_rate=75,
        is_peak_hour=1
    )
    
    print("\n" + "="*50)
    print("PARKING CONGESTION PREDICTION")
    print("="*50)
    print(f"Congestion Score: {result['congestion_score']}/100")
    print(f"Status: {result['status'].upper()}")
    print(f"Color: {result['color']}")
    print(f"Occupancy: {result['occupancy_rate']}%")
    print("\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  {rec}")
    print("="*50)