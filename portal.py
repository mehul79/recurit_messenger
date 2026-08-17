import os
import time
import httpx
from dotenv import load_dotenv
from state import get_session, Meta

load_dotenv()

DEFAULT_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtxb3FnemhqbW12dmhnZXZ5ZnBoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgzMzUzNjIsImV4cCI6MjA4MzkxMTM2Mn0.b1MjosrjZ0HIbb1Lx0KthlDTgqRB7C9OIqrCV03ahUc"

def get_supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "https://api.recruit.thapar.edu").strip().rstrip("/")

def get_supabase_anon() -> str:
    raw = os.getenv("SUPABASE_ANON", "")
    if not raw:
        return DEFAULT_ANON_KEY
    return "".join(raw.split())

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
    
    return os.getenv("PORTAL_REFRESH_TOKEN", "").strip()

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

def login_with_password() -> str:
    email = os.getenv("PORTAL_EMAIL", "mgupta6_be23@thapar.edu")
    password = os.getenv("PORTAL_PASSWORD", "Alpha@123")
    
    url = f"{get_supabase_url()}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": get_supabase_anon(),
        "Content-Type": "application/json"
    }
    payload = {"email": email, "password": password}

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in", 3600)
            update_stored_tokens(access_token, refresh_token, expires_in)
            print("Successfully authenticated via email & password fallback!")
            return access_token
        else:
            raise RuntimeError(f"Failed email/password authentication (HTTP {resp.status_code}): {resp.text}")

def refresh_access_token() -> str:
    refresh_token = get_stored_refresh_token()
    if not refresh_token:
        return login_with_password()
    
    url = f"{get_supabase_url()}/auth/v1/token?grant_type=refresh_token"
    headers = {
        "apikey": get_supabase_anon(),
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
            print(f"Refresh token failed (HTTP {resp.status_code}): {resp.text}. Falling back to email/password login...")
            return login_with_password()

def get_valid_access_token() -> str:
    global _token_cache
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["access_token"]
    return refresh_access_token()

def fetch_student_profile(token: str) -> dict:
    url = f"{get_supabase_url()}/rest/v1/students?select=*"
    headers = {
        "apikey": get_supabase_anon(),
        "Authorization": f"Bearer {token}"
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200 and resp.json():
                return resp.json()[0]
    except Exception as e:
        print(f"Warning: Failed to fetch student profile: {e}")
    return {}

def is_student_eligible_for_job(job: dict, student: dict) -> tuple[bool, str]:
    if not student:
        return True, ""

    student_cgpa = float(student.get("cgpa") or 0.0)
    student_batch = str(student.get("batch") or student.get("passing_year") or "2027")
    student_branch = str(student.get("branch") or student.get("department") or "").lower()

    eligibilities = job.get("job_eligibilities") or []
    if not eligibilities or not isinstance(eligibilities, list):
        return True, ""

    el = eligibilities[0] if len(eligibilities) > 0 else {}
    
    # 1. Min CGPA Check
    min_gpa = el.get("min_gpa")
    if min_gpa is not None:
        try:
            if student_cgpa < float(min_gpa):
                return False, f"CGPA {student_cgpa} < min required {min_gpa}"
        except ValueError:
            pass

    # 2. Batch Check
    eligible_batches = el.get("eligible_batches") or []
    if eligible_batches and isinstance(eligible_batches, list):
        str_batches = [str(b) for b in eligible_batches]
        if student_batch not in str_batches and not any(student_batch in b for b in str_batches):
            return False, f"Batch {student_batch} not in eligible batches {str_batches}"

    # 3. Branch Check
    eligible_branches = el.get("eligible_branches") or el.get("branches") or []
    if eligible_branches and isinstance(eligible_branches, list):
        str_branches = [str(b).lower() for b in eligible_branches]
        if student_branch and not any(student_branch in b or b in student_branch for b in str_branches):
            return False, f"Branch {student_branch} not in eligible branches {str_branches}"

    return True, ""

def fetch_eligible_jobs() -> list:
    """
    Fetch live approved campus jobs and filter strictly against the student's batch, branch, and CGPA.
    """
    token = get_valid_access_token()
    student = fetch_student_profile(token)

    url = f"{get_supabase_url()}/rest/v1/job_university_mappings?select=*,jobs_posted(*,companies(*),job_salaries(*),job_eligibilities(*))&status=eq.Approved&order=approved_at.desc.nullslast&limit=40"
    headers = {
        "apikey": get_supabase_anon(),
        "Authorization": f"Bearer {token}"
    }
    
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
        if resp.status_code == 200:
            mappings = resp.json()
            formatted_jobs = []
            for m in mappings:
                jp = m.get("jobs_posted") or {}
                company_info = jp.get("companies") or {}
                company_name = company_info.get("name") if isinstance(company_info, dict) else "Company"

                job_id = str(jp.get("id") or m.get("job_id") or "")
                if not job_id:
                    continue

                # Strict Student Eligibility Check (Batch, Branch, CGPA)
                eligible, reason = is_student_eligible_for_job(jp, student)
                if not eligible:
                    print(f"Skipping ineligible job for student profile: {company_name} - {jp.get('title')} ({reason})")
                    continue

                salaries = jp.get("job_salaries") or []
                stipend_val = "N/A"
                ctc_val = ""
                if salaries and isinstance(salaries, list) and len(salaries) > 0:
                    sal = salaries[0]
                    if sal.get("stipend"):
                        stipend_val = f"₹{sal.get('stipend'):,}/pm"
                    if sal.get("ctc"):
                        ctc_val = f"₹{sal.get('ctc'):,}"

                formatted_jobs.append({
                    "job_id": job_id,
                    "id": job_id,
                    "title": jp.get("title") or "Role",
                    "company": company_name,
                    "company_name": company_name,
                    "stipend": stipend_val,
                    "ctc": ctc_val,
                    "deadline": jp.get("application_deadline") or m.get("approved_at") or jp.get("created_at"),
                    "location": jp.get("location") or "",
                    "link": f"https://recruit.thapar.edu/student/jobs",
                    "raw_json": jp
                })
            return formatted_jobs
        else:
            print(f"Error fetching job_university_mappings (HTTP {resp.status_code}): {resp.text}")
            return []

def fetch_applied_job_ids() -> set:
    """
    Fetch set of applied job IDs for student from applications table.
    """
    token = get_valid_access_token()
    url = f"{get_supabase_url()}/rest/v1/applications?select=job_id"
    headers = {
        "apikey": get_supabase_anon(),
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
