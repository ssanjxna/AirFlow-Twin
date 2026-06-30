import pandas as pd
import os
from datetime import datetime, timedelta
from database.db import get_connection

class AirportDataLoader:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.flights_df = None
        self.gate_events_df = None
        self.maintenance_df = None
        self.passengers_df = None

    def _to_int(self, value, default=0):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _to_float(self, value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _build_flight_payload(self, row):
        # Column mapping based on the generated flights dataset.
        flight_id = str(row.iloc[0])

        # Skip header rows or invalid records.
        if flight_id.isdigit() or len(flight_id) < 3 or flight_id == '0':
            return None

        airline_code = str(row.iloc[2])[:2] if pd.notna(row.iloc[2]) else 'UK'
        origin = str(row.iloc[3]) if pd.notna(row.iloc[3]) else 'DEL'
        destination = str(row.iloc[4]) if pd.notna(row.iloc[4]) else 'DXB'
        delay = self._to_float(row.iloc[14], 0)
        risk_score = min(100, int(abs(delay) / 30 * 100)) if delay else 25
        terminal = str(row.iloc[16]) if pd.notna(row.iloc[16]) else 'T1'
        gate = str(row.iloc[17]) if pd.notna(row.iloc[17]) else 'A1'
        distance = self._to_int(row.iloc[19], 5000)
        time_of_day = str(row.iloc[27]) if pd.notna(row.iloc[27]) else 'Morning'
        day_of_week = str(row.iloc[28]) if pd.notna(row.iloc[28]) else 'Mon'
        season = str(row.iloc[30]) if pd.notna(row.iloc[30]) else 'Summer'
        flight_type = str(row.iloc[31]) if pd.notna(row.iloc[31]) else 'Passenger'
        passenger_count = max(80, self._to_int(row.iloc[25], 180))
        load_factor = max(0.1, min(1.0, self._to_float(row.iloc[26], 0.8)))
        baggage_count = max(40, int(passenger_count * 0.65))
        delay_reason = str(row.iloc[15]) if pd.notna(row.iloc[15]) else 'Operational'
        status = str(row.iloc[13]) if pd.notna(row.iloc[13]) else 'Scheduled'
        aircraft_type = str(row.iloc[9]) if pd.notna(row.iloc[9]) else 'A320'
        registration = str(row.iloc[10]) if pd.notna(row.iloc[10]) else ''
        maintenance_required = int(delay_reason.upper() in {'TECH', 'MTC', 'MAINTENANCE'})

        try:
            dep_time_str = str(row.iloc[5])
            scheduled_departure = dep_time_str.split(' ')[1][:5] if ' ' in dep_time_str else '10:00'
        except Exception:
            scheduled_departure = '10:00'

        lat, lng = self._get_gate_position(gate)

        return {
            "id": flight_id,
            "lat": lat,
            "lng": lng,
            "status": status,
            "risk": risk_score,
            "gate": gate,
            "terminal": terminal,
            "origin": origin,
            "destination": destination,
            "airline_code": airline_code,
            "distance": distance,
            "time_of_day": time_of_day,
            "day_of_week": day_of_week,
            "season": season,
            "flight_type": flight_type,
            "scheduled_departure": scheduled_departure,
            "aircraft_type": aircraft_type,
            "registration": registration,
            "delay_minutes": int(delay),
            "delay_reason": delay_reason,
            "passenger_count": passenger_count,
            "load_factor": load_factor,
            "baggage_count": baggage_count,
            "maintenance_required": maintenance_required,
        }
        
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
    
    def get_total_flights_count(self):
        """Get the total count of flights from the database flights table"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM flights")
            result = cursor.fetchone()
            conn.close()
            
            count = result[0] if result else 0
            return max(1, count)
        except Exception as e:
            print(f"Error getting flight count from database: {e}")
            # Fallback to CSV count if database query fails
            return max(1, len(self.flights_df)) if self.flights_df is not None else 1
    
    def get_current_flights(self, limit=15):
        if self.flights_df is None:
            return self._get_mock_flights(limit)
        
        sample_flights = self.flights_df if limit is None else self.flights_df.head(limit)
        
        flights_list = []
        for idx, row in sample_flights.iterrows():
            try:
                flight_data = self._build_flight_payload(row)
                if flight_data:
                    flights_list.append(flight_data)
            except Exception as e:
                print(f"Error processing row {idx}: {e}")
                continue
        
        return flights_list

    def get_flight_by_id(self, flight_id):
        if self.flights_df is None:
            return next((flight for flight in self._get_mock_flights(5) if flight["id"] == flight_id), None)

        matches = self.flights_df[self.flights_df.iloc[:, 0].astype(str) == str(flight_id)]

        if matches.empty:
            return None

        return self._build_flight_payload(matches.iloc[0])
    
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
