import importlib


def test_events_endpoint_returns_live_predictions():
    mod = importlib.import_module('app')
    client = mod.app.test_client()

    response = client.post('/api/predict/events', json={'time_horizon': 15})
    assert response.status_code == 200
    payload = response.get_json()
    assert 'events' in payload
    assert isinstance(payload['events'], list)


def test_parking_status_endpoint_returns_model_metrics():
    mod = importlib.import_module('app')
    client = mod.app.test_client()

    response = client.get('/api/parking_status')
    assert response.status_code == 200
    payload = response.get_json()
    assert 'congestion_score' in payload
    assert 'status' in payload
    assert 'color' in payload
