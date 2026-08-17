import os
import json
import httpx
from state import get_session, Meta
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://api.recruit.thapar.edu")
SUPABASE_ANON = os.getenv("SUPABASE_ANON")

def sync_and_fetch():
    session = get_session()
    meta_row = session.query(Meta).filter(Meta.key == "refresh_token").first()
    db_refresh_token = meta_row.value if meta_row else None
    session.close()

    print(f"Latest refresh_token from PostgreSQL DB meta table: {db_refresh_token[:25] if db_refresh_token else 'None'}...")

    token_to_use = db_refresh_token or os.getenv("PORTAL_REFRESH_TOKEN")

    # Refresh access token
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token"
    headers = {
        "apikey": SUPABASE_ANON,
        "Content-Type": "application/json"
    }
    payload = {"refresh_token": token_to_use}

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        print(f"Token Refresh HTTP Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token")
            print("Access Token obtained successfully!")

            # Update .env and DB meta
            if new_refresh_token:
                session = get_session()
                row = session.query(Meta).filter(Meta.key == "refresh_token").first()
                if not row:
                    row = Meta(key="refresh_token", value=new_refresh_token)
                    session.add(row)
                else:
                    row.value = new_refresh_token
                session.commit()
                session.close()

            # Query most recent job
            jobs_url = f"{SUPABASE_URL}/rest/v1/jobs_posted?select=*,companies(*),job_salaries(*)&order=created_at.desc&limit=5"
            job_headers = {
                "apikey": SUPABASE_ANON,
                "Authorization": f"Bearer {access_token}"
            }
            job_resp = client.get(jobs_url, headers=job_headers)
            print(f"Jobs Fetch HTTP Status: {job_resp.status_code}")
            if job_resp.status_code == 200:
                jobs = job_resp.json()
                print("\n" + "="*70)
                print(f"MOST RECENT JOB ON RECRUITSAGE ({len(jobs)} total fetched):")
                print("="*70)
                for i, j in enumerate(jobs[:3], 1):
                    company_info = j.get("companies") or {}
                    company_name = company_info.get("name") if isinstance(company_info, dict) else "Company"
                    title = j.get("title") or "Role"
                    created_at = j.get("created_at") or "N/A"
                    location = j.get("location") or "N/A"
                    job_id = j.get("id")

                    salaries = j.get("job_salaries") or []
                    stipend = "N/A"
                    ctc = "N/A"
                    if salaries and isinstance(salaries, list) and len(salaries) > 0:
                        sal = salaries[0]
                        if sal.get("stipend"):
                            stipend = f"INR {sal.get('stipend'):,}/pm"
                        if sal.get("ctc"):
                            ctc = f"INR {sal.get('ctc'):,}"

                    print(f"#{i} {company_name} - {title}")
                    print(f"   Posted Date (created_at): {created_at}")
                    print(f"   Stipend: {stipend} | CTC: {ctc}")
                    print(f"   Location: {location}")
                    print(f"   Job ID: {job_id}")
                    print("-" * 70)
        else:
            print("Refresh failed:", resp.text)

if __name__ == "__main__":
    sync_and_fetch()
