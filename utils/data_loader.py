import pandas as pd
import os
from datetime import datetime, timedelta

class AirportDataLoader:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.flights_df = None
        self.gate_events_df = None
        self.maintenance_df = None
        self.passengers_df = None

    def _read_dataset(self, filename):
        dataset_path = os.path.join(self.data_dir, filename)

        if not os.path.exists(dataset_path):
            return None

        with open(dataset_path, 'r', encoding='utf-8') as handle:
            first_row = handle.readline().strip().split(',')

        numeric_header = [str(index) for index in range(len(first_row))]

        if first_row == numeric_header:
            return pd.read_csv(dataset_path)

        return pd.read_csv(dataset_path, header=None)
        
    def load_all_datasets(self):
        self.flights_df = self._read_dataset('flights.csv')
        if self.flights_df is not None:
            print(f"Loaded {len(self.flights_df)} flights")
        
        self.gate_events_df = self._read_dataset('gate_events.csv')
        if self.gate_events_df is not None:
            print(f"Loaded {len(self.gate_events_df)} gate events")
        
        self.maintenance_df = self._read_dataset('maintenance_logs.csv')
        if self.maintenance_df is not None:
            print(f"Loaded {len(self.maintenance_df)} maintenance records")
            
        self.passengers_df = self._read_dataset('passengers.csv')
        if self.passengers_df is not None:
            print(f"Loaded {len(self.passengers_df)} passenger records")
    
    def get_current_flights(self, limit=15):
        if self.flights_df is None:
            return self._get_mock_flights(limit)
        
        sample_flights = self.flights_df.head(limit)
        
        flights_list = []
        for idx, row in sample_flights.iterrows():
            # Column mapping based on your data
            try:
                flight_id = str(row.iloc[0])
                # Skip header rows or invalid data
                if flight_id.isdigit() or len(flight_id) < 3 or flight_id == '0':
                    continue
                    
                airline_code = str(row.iloc[2])[:2] if pd.notna(row.iloc[2]) else 'UK'
                origin = str(row.iloc[3]) if pd.notna(row.iloc[3]) else 'DEL'
                destination = str(row.iloc[4]) if pd.notna(row.iloc[4]) else 'DXB'
                
                # Get delay (column 14)
                try:
                    delay = float(row.iloc[14]) if pd.notna(row.iloc[14]) else 0
                    risk_score = min(100, int(abs(delay) / 30 * 100))
                except:
                    risk_score = 50
                
                # Get gate (column 17)
                gate = str(row.iloc[17]) if pd.notna(row.iloc[17]) else 'A1'
                
                # Get distance (column 19)
                try:
                    distance = int(float(row.iloc[19])) if pd.notna(row.iloc[19]) else 5000
                except:
                    distance = 5000
                
                # Get time of day (column 27)
                time_of_day = str(row.iloc[27]) if pd.notna(row.iloc[27]) else 'Morning'
                
                # Get day of week (column 28)
                day_of_week = str(row.iloc[28]) if pd.notna(row.iloc[28]) else 'Mon'
                
                # Get scheduled departure time (column 5)
                try:
                    dep_time_str = str(row.iloc[5])
                    scheduled_departure = dep_time_str.split(' ')[1][:5] if ' ' in dep_time_str else '10:00'
                except:
                    scheduled_departure = '10:00'
                
                # Get status (column 13)
                status = str(row.iloc[13]) if pd.notna(row.iloc[13]) else 'Scheduled'
                
                # Get aircraft type (column 9)
                aircraft_type = str(row.iloc[9]) if pd.notna(row.iloc[9]) else 'A320'
                
                # Calculate position based on gate
                lat, lng = self._get_gate_position(gate)
                
                flight_data = {
                    "id": flight_id,
                    "lat": lat,
                    "lng": lng,
                    "status": status,
                    "risk": risk_score,
                    "gate": gate,
                    "origin": origin,
                    "destination": destination,
                    "airline_code": airline_code,
                    "distance": distance,
                    "time_of_day": time_of_day,
                    "day_of_week": day_of_week,
                    "scheduled_departure": scheduled_departure,
                    "aircraft_type": aircraft_type,
                    "delay_minutes": int(delay) if 'delay' in locals() else 0
                }
                flights_list.append(flight_data)
            except Exception as e:
                print(f"Error processing row {idx}: {e}")
                continue
        
        return flights_list
    
    def _get_gate_position(self, gate):
        # Map gates to realistic airport positions (Dubai Airport coordinates)
        gate_positions = {
            'A1': (25.2520, 55.3640), 'A2': (25.2522, 55.3642), 'A3': (25.2524, 55.3644),
            'B1': (25.2530, 55.3650), 'B2': (25.2532, 55.3652), 'B3': (25.2534, 55.3654),
            'B12': (25.2540, 55.3660), 'B50': (25.2550, 55.3670),
            'C1': (25.2560, 55.3680), 'C2': (25.2562, 55.3682), 'C3': (25.2564, 55.3684),
            'T3': (25.2532, 55.3657), 'T1': (25.2510, 55.3630),
        }
        return gate_positions.get(gate, (25.2532 + (hash(gate) % 10) * 0.0001, 55.3657 + (hash(gate) % 10) * 0.0001))
    
    def get_resource_status(self):
        resources = {
            "maintenance_crews": 5,
            "fuel_trucks": 8,
            "baggage_carts": 15,
            "available_crews": 3,
            "available_trucks": 6,
            "available_carts": 12
        }
        
        if self.maintenance_df is not None:
            try:
                active_count = len(self.maintenance_df[self.maintenance_df.iloc[:, 2] == 'IN_PROGRESS'])
                resources["available_crews"] = max(0, resources["maintenance_crews"] - active_count)
            except:
                pass
        
        return resources
    
    def _get_mock_flights(self, limit):
        return [
            {
                "id": "UK-633", "lat": 25.2532, "lng": 55.3657, "status": "Landed", 
                "risk": 62, "gate": "B3", "origin": "DEL", "destination": "SIN", 
                "airline_code": "UK", "distance": 9330, "time_of_day": "Morning", 
                "day_of_week": "Mon", "scheduled_departure": "10:00", "aircraft_type": "A350", "delay_minutes": 30
            },
            {
                "id": "BA-6017", "lat": 25.2540, "lng": 55.3660, "status": "Taxiing", 
                "risk": 64, "gate": "B12", "origin": "DEL", "destination": "DXB", 
                "airline_code": "BA", "distance": 5766, "time_of_day": "Morning", 
                "day_of_week": "Sat", "scheduled_departure": "10:15", "aircraft_type": "A350", "delay_minutes": 0
            }
        ][:limit]
