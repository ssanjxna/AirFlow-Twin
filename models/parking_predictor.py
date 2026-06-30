from datetime import datetime
from pathlib import Path

from loaders.backend_loader_congestion_predictor import load_artifact, predict_congestion


class ParkingCongestionPredictor:
    def __init__(self, model_path=None):
        self.model_path = Path(model_path) if model_path else Path(__file__).resolve().parent.parent / "models" / "airflow_congestion_predictor_artifact.pkl"
        self.artifact = None
        self.is_loaded = False

    def load_model(self):
        self.artifact = load_artifact(self.model_path)
        self.is_loaded = True
        print(f"Congestion artifact loaded from {self.model_path.name}")
        return True

    def train(self):
        raise RuntimeError(
            "Parking predictor does not train or save parking_*.pkl files. "
            "Use airflow_congestion_predictor_artifact.pkl only."
        )

    def _build_airport_features(
        self,
        hour=None,
        day_type="weekday",
        weather="clear",
        flights_arriving=5,
        occupancy_rate=50,
        is_peak_hour=0,
    ):
        now = datetime.now()
        hour = now.hour if hour is None else int(hour)

        adjusted_occupancy = float(occupancy_rate)
        if weather == "rain":
            adjusted_occupancy = min(100.0, adjusted_occupancy + 10)
        elif weather == "snow":
            adjusted_occupancy = min(100.0, adjusted_occupancy + 15)

        passenger_count = max(80, min(320, int(120 + adjusted_occupancy)))
        baggage_count = max(50, int(passenger_count * 0.7))
        flights_same_hour = max(1, int(flights_arriving))
        passengers_same_hour = flights_same_hour * passenger_count
        baggage_same_hour = flights_same_hour * baggage_count

        season = (
            "Winter" if now.month in {12, 1, 2}
            else "Spring" if now.month in {3, 4, 5}
            else "Summer" if now.month in {6, 7, 8}
            else "Autumn"
        )

        return {
            "terminal": "T1" if adjusted_occupancy < 75 else "T2",
            "gate": "A1" if adjusted_occupancy < 60 else "B12",
            "airline_code": "UK",
            "aircraft_type": "A320",
            "origin": "DEL",
            "destination": "SIN",
            "is_international": 1,
            "passenger_count": passenger_count,
            "baggage_count": baggage_count,
            "load_factor": round(max(0.2, min(1.0, adjusted_occupancy / 100)), 2),
            "time_of_day": "Morning" if hour < 12 else "Afternoon" if hour < 17 else "Evening",
            "day_of_week": "Sat" if day_type == "weekend" else "Mon",
            "is_weekend": 1 if day_type == "weekend" else 0,
            "season": season,
            "flight_type": "Passenger",
            "departure_hour": hour,
            "departure_month": now.month,
            "is_peak_hour": int(is_peak_hour),
            "flights_same_hour": flights_same_hour,
            "passengers_same_hour": passengers_same_hour,
            "baggage_same_hour": baggage_same_hour,
        }

    def predict(
        self,
        hour=None,
        day_type="weekday",
        weather="clear",
        flights_arriving=5,
        occupancy_rate=50,
        is_peak_hour=0,
    ):
        if not self.is_loaded:
            self.load_model()

        congestion = predict_congestion(
            self.artifact,
            self._build_airport_features(
                hour=hour,
                day_type=day_type,
                weather=weather,
                flights_arriving=flights_arriving,
                occupancy_rate=occupancy_rate,
                is_peak_hour=is_peak_hour,
            ),
        )

        probabilities = congestion["probabilities"]
        congestion_score = round(
            probabilities["Low"] * 0.25 +
            probabilities["Medium"] * 0.60 +
            probabilities["High"] * 0.90,
            2,
        )

        if congestion_score < 30:
            status = "low"
            color = "green"
        elif congestion_score < 60:
            status = "normal"
            color = "yellow"
        elif congestion_score < 85:
            status = "high"
            color = "orange"
        else:
            status = "critical"
            color = "red"

        return {
            "congestion_score": congestion_score,
            "status": status,
            "color": color,
            "occupancy_rate": round(float(occupancy_rate), 2),
            "recommendations": self._get_recommendations(status),
            "model_version": congestion["model_version"],
            "congestion_level": congestion["congestion_level"],
            "probabilities": probabilities,
        }

    def _get_recommendations(self, status):
        if status == "critical":
            return [
                "Open overflow parking P3 and P4 immediately",
                "Activate dynamic signage to redirect traffic",
                "Send SMS alerts to incoming passengers",
                "Coordinate with ride-share for alternative drop-off",
            ]
        if status == "high":
            return [
                "Prepare overflow parking P3",
                "Display 'Parking Full' messages on highway signs",
                "Deploy staff to direct traffic",
            ]
        if status == "normal":
            return [
                "Standard operations",
                "Monitor occupancy levels",
            ]
        return [
            "Parking capacity adequate",
            "No action needed",
        ]
