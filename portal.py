import os
import time
import httpx
from dotenv import load_dotenv
from state import get_session, Meta

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://api.recruit.thapar.edu")
SUPABASE_ANON = os.getenv("SUPABASE_ANON")

_token_cache = {
    "access_token": None,
    "expires_at": 0
}

def get_stored_refresh_token() -> str:
    session = get_session()
    try:
        meta_row = session.query(Meta).filter(Meta.key == "refresh_token").first()
        if meta_row and meta_row.value:
            session.close()
            return meta_row.value
    except Exception:
        pass
    finally:
        session.close()
    
    return os.getenv("PORTAL_REFRESH_TOKEN", "")

def update_stored_tokens(access_token: str, refresh_token: str, expires_in: int = 3600):
    global _token_cache
    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = time.time() + (expires_in - 60)

    session = get_session()
    try:
        row = session.query(Meta).filter(Meta.key == "refresh_token").first()
        if not row:
            row = Meta(key="refresh_token", value=refresh_token)
            session.add(row)
        else:
            row.value = refresh_token
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Warning: Failed to save refresh_token to DB: {e}")
    finally:
        session.close()

def refresh_access_token() -> str:
    refresh_token = get_stored_refresh_token()
    if not refresh_token:
        raise ValueError("No PORTAL_REFRESH_TOKEN found in .env or database meta table!")
    
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token"
    headers = {
        "apikey": SUPABASE_ANON,
        "Content-Type": "application/json"
    }
    payload = {"refresh_token": refresh_token}
    
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            new_access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token", refresh_token)
            expires_in = data.get("expires_in", 3600)
            update_stored_tokens(new_access_token, new_refresh_token, expires_in)
            return new_access_token
        else:
            raise RuntimeError(f"Failed to refresh Supabase access token (HTTP {resp.status_code}): {resp.text}")

def get_valid_access_token() -> str:
    global _token_cache
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["access_token"]
    return refresh_access_token()

def fetch_eligible_jobs() -> list:
    """
    Fetch live posted jobs with company and salary details directly from PostgREST tables.
    """
    token = get_valid_access_token()
    url = f"{SUPABASE_URL}/rest/v1/jobs_posted?select=*,companies(*),job_salaries(*)&order=created_at.desc&limit=25"
    headers = {
        "apikey": SUPABASE_ANON,
        "Authorization": f"Bearer {token}"
    }
    
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
        if resp.status_code == 200:
            raw_jobs = resp.json()
            formatted_jobs = []
            for j in raw_jobs:
                company_info = j.get("companies") or {}
                company_name = company_info.get("name") if isinstance(company_info, dict) else "Company"

                salaries = j.get("job_salaries") or []
                stipend_val = "N/A"
                ctc_val = ""
                if salaries and isinstance(salaries, list) and len(salaries) > 0:
                    sal = salaries[0]
                    if sal.get("stipend"):
                        stipend_val = f"₹{sal.get('stipend'):,}/pm"
                    if sal.get("ctc"):
                        ctc_val = f"₹{sal.get('ctc'):,}"

                formatted_jobs.append({
                    "job_id": str(j.get("id")),
                    "id": str(j.get("id")),
                    "title": j.get("title") or "Role",
                    "company": company_name,
                    "company_name": company_name,
                    "stipend": stipend_val,
                    "ctc": ctc_val,
                    "deadline": j.get("application_deadline") or j.get("created_at"),
                    "location": j.get("location") or "",
                    "link": f"https://recruit.thapar.edu/job/{j.get('id')}",
                    "raw_json": j
                })
            return formatted_jobs
        else:
            print(f"Error fetching jobs_posted (HTTP {resp.status_code}): {resp.text}")
            return []

def fetch_applied_job_ids() -> set:
    """
    Fetch set of applied job IDs for student from applications table.
    """
    token = get_valid_access_token()
    url = f"{SUPABASE_URL}/rest/v1/applications?select=job_id"
    headers = {
        "apikey": SUPABASE_ANON,
        "Authorization": f"Bearer {token}"
    }
    
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return {str(item["job_id"]) for item in data if "job_id" in item}
        else:
            print(f"Error fetching applications (HTTP {resp.status_code}): {resp.text}")
            return set()
