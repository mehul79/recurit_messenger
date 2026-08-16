from fastapi.testclient import TestClient
from app import app, TICK_SECRET

def test_routes():
    print("=== Testing FastAPI Application Routes ===")
    client = TestClient(app)
    
    # 1. Health endpoint
    res = client.get("/health")
    print(f"GET /health status: {res.status_code}, body: {res.json()}")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    
    # 2. Action endpoint (/act)
    act_url = f"/act?job=test_job_123&a=optout&secret={TICK_SECRET}"
    res_act = client.post(act_url)
    print(f"POST /act (optout) status: {res_act.status_code}")
    assert res_act.status_code == 200
    assert "Opted Out" in res_act.text
    
    ack_url = f"/act?job=test_job_123&a=ack&secret={TICK_SECRET}"
    res_ack = client.post(ack_url)
    print(f"POST /act (ack) status: {res_ack.status_code}")
    assert res_ack.status_code == 200
    assert "Acknowledged" in res_ack.text
    
    # 3. Invalid secret test
    res_invalid = client.post(f"/act?job=test_job_123&a=optout&secret=wrong_secret")
    print(f"POST /act with invalid secret status: {res_invalid.status_code}")
    assert res_invalid.status_code == 403

    print("ALL FastAPI route tests PASSED!")

if __name__ == "__main__":
    test_routes()
