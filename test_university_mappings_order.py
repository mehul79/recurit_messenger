import os
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "https://api.recruit.thapar.edu"
SUPABASE_ANON = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtxb3FnemhqbW12dmhnZXZ5ZnBoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgzMzUzNjIsImV4cCI6MjA4MzkxMTM2Mn0.b1MjosrjZ0HIbb1Lx0KthlDTgqRB7C9OIqrCV03ahUc"

def test_mappings():
    # If refresh token is available in .env or arguments
    token = os.getenv("PORTAL_REFRESH_TOKEN")
    print("=== Querying job_university_mappings ===")
    
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token"
    headers = {"apikey": SUPABASE_ANON, "Content-Type": "application/json"}
    
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, headers=headers, json={"refresh_token": token})
        if resp.status_code == 200:
            access_token = resp.json().get("access_token")
            auth_headers = {"apikey": SUPABASE_ANON, "Authorization": f"Bearer {access_token}"}
            
            map_url = f"{SUPABASE_URL}/rest/v1/job_university_mappings?select=*,jobs_posted(*,companies(*))&status=eq.Approved&order=approved_at.desc.nullslast&limit=25"
            map_resp = client.get(map_url, headers=auth_headers)
            print(f"Status: {map_resp.status_code}")
            if map_resp.status_code == 200:
                mappings = map_resp.json()
                print(f"Total Approved Job Mappings Found: {len(mappings)}")
                print("="*70)
                for i, m in enumerate(mappings, 1):
                    jp = m.get("jobs_posted") or {}
                    company_data = jp.get("companies") or {}
                    company_name = company_data.get("name") if isinstance(company_data, dict) else "Company"
                    title = jp.get("title") or "Role"
                    approved_at = m.get("approved_at") or m.get("created_at") or "N/A"
                    print(f"[{i}] {company_name} - {title} | Approved: {approved_at} | Mapping ID: {m.get('id')}")
            else:
                print("Error fetching mappings:", map_resp.text)

if __name__ == "__main__":
    test_mappings()
