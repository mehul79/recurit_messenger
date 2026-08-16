import httpx
from portal import get_valid_access_token, SUPABASE_URL, SUPABASE_ANON

def test_endpoints():
    token = get_valid_access_token()
    headers = {
        "apikey": SUPABASE_ANON,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    rpc_candidates = [
        "get_student_dashboard_data",
        "get_eligible_jobs",
        "get_student_eligible_jobs",
        "get_eligible_jobs_rpc",
        "get_student_user_id",
        "check_comprehensive_eligibility"
    ]

    table_candidates = [
        "job_postings",
        "job_applications",
        "applications",
        "jobs",
        "students",
        "companies"
    ]

    print("=== Testing RPC Candidates ===")
    with httpx.Client(timeout=10.0) as client:
        for rpc in rpc_candidates:
            url = f"{SUPABASE_URL}/rest/v1/rpc/{rpc}"
            resp = client.post(url, headers=headers, json={})
            print(f"RPC '{rpc}': HTTP {resp.status_code}")
            if resp.status_code in (200, 400):
                print(f" -> Response: {resp.text[:300]}")

        print("\n=== Testing Table Candidates ===")
        for tbl in table_candidates:
            url = f"{SUPABASE_URL}/rest/v1/{tbl}?select=*&limit=2"
            resp = client.get(url, headers=headers)
            print(f"Table '{tbl}': HTTP {resp.status_code}")
            if resp.status_code == 200:
                print(f" -> Sample data count: {len(resp.json())}")
                print(f" -> Sample row: {resp.text[:300]}")

if __name__ == "__main__":
    test_endpoints()
