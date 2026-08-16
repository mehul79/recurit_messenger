import json
import httpx
from portal import get_valid_access_token, SUPABASE_URL, SUPABASE_ANON

def test_fetch():
    token = get_valid_access_token()
    headers = {
        "apikey": SUPABASE_ANON,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("=== Querying jobs_posted ===")
    url = f"{SUPABASE_URL}/rest/v1/jobs_posted?select=*,companies(*)&order=created_at.desc&limit=10"
    
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
        print(f"HTTP Status: {resp.status_code}")
        if resp.status_code == 200:
            jobs = resp.json()
            print(f"Found {len(jobs)} jobs in jobs_posted:")
            for i, j in enumerate(jobs, 1):
                company_data = j.get("companies") or {}
                company_name = company_data.get("name") if isinstance(company_data, dict) else "Company"
                title = j.get("title") or j.get("job_title") or j.get("role") or "Role"
                deadline = j.get("deadline") or j.get("last_date") or j.get("application_deadline") or "N/A"
                print(f" [{i}] {company_name} · {title} (ID: {j.get('id')}) | Deadline: {deadline}")
                print(f"     Fields: {list(j.keys())}")
        else:
            print("Error response:", resp.text)

    print("\n=== Querying student applications ===")
    app_url = f"{SUPABASE_URL}/rest/v1/applications?select=job_id"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(app_url, headers=headers)
        if resp.status_code == 200:
            apps = resp.json()
            applied_ids = [a["job_id"] for a in apps if "job_id" in a]
            print(f"Total Applied Jobs: {len(applied_ids)}")
            print("Applied Job IDs:", applied_ids[:5])

if __name__ == "__main__":
    test_fetch()
