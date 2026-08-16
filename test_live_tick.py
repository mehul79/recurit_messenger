from fastapi.testclient import TestClient
from app import app, TICK_SECRET

def test_live_tick():
    print("=== Testing Live /tick State Machine Execution ===")
    client = TestClient(app)
    
    response = client.post(f"/tick?secret={TICK_SECRET}")
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.json()}")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    print("\nSUCCESS! Live /tick executed cleanly!")

if __name__ == "__main__":
    test_live_tick()
