from fastapi import FastAPI
from services.simulation_service import run_simulation

app = FastAPI(title="AirFlow Twin API")

@app.get("/")
def root():
    return {"message": "AirFlow Twin API running"}

@app.post("/simulate")
def simulate():
    return run_simulation()