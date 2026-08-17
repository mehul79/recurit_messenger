import os
import time
import httpx
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from dotenv import load_dotenv
from state import get_session, Meta

load_dotenv()

def log(msg: str):
    """Job titles carry U+202F etc; a cp1252 console would raise on a bare print()."""
    try:
        print(str(msg).encode("ascii", errors="replace").decode("ascii"), flush=True)
    except Exception:
        pass

DEFAULT_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtxb3FnemhqbW12dmhnZXZ5ZnBoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgzMzUzNjIsImV4cCI6MjA4MzkxMTM2Mn0.b1MjosrjZ0HIbb1Lx0KthlDTgqRB7C9OIqrCV03ahUc"

def get_supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "https://api.recruit.thapar.edu").strip().rstrip("/")

def get_supabase_anon() -> str:
    raw = os.getenv("SUPABASE_ANON", "")
    if not raw:
        return DEFAULT_ANON_KEY
    return "".join(raw.split())


class AuthDead(Exception):
    """The refresh-token chain is broken. Only a human re-seed can fix it."""

# Password grant is Turnstile-gated server-side, so refresh-token rotation is the ONLY
# usable auth path. The chain survives exactly as long as every rotated token is
# persisted, so: one refresher at a time (advisory lock), and the new token is committed
# before the access token is handed out.
AUTH_LOCK_ID = 918273645
_ACCESS_SKEW = 300  # refresh 5 min early

_META_KEYS = ("refresh_token", "access_token", "access_expires_at", "auth_alert_sent")
_token_cache = {"access_token": None, "expires_at": 0}

def _meta_put(session, rows: dict, key: str, value: str):
    row = rows.get(key)
    if row is None:
        session.add(Meta(key=key, value=value))
    else:
        row.value = value

def _refresh_grant(refresh_token: str) -> dict:
    url = f"{get_supabase_url()}/auth/v1/token?grant_type=refresh_token"
    headers = {"apikey": get_supabase_anon(), "Content-Type": "application/json"}
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, headers=headers, json={"refresh_token": refresh_token})
    if resp.status_code != 200:
        raise AuthDead(f"refresh_token grant rejected (HTTP {resp.status_code}): {resp.text}")
    data = resp.json()
    if not data.get("access_token"):
        raise AuthDead(f"refresh_token grant returned no access_token: {resp.text}")
    return data

def get_valid_access_token() -> str:
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["access_token"]

    session = get_session()
    try:
        # Serialize across workers/instances; released when the txn ends.
        session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": AUTH_LOCK_ID})
        rows = {m.key: m for m in session.query(Meta).filter(
            Meta.key.in_(_META_KEYS)).all()}

        # Someone else may have refreshed while we waited on the lock.
        cached = rows.get("access_token")
        exp_row = rows.get("access_expires_at")
        exp = float(exp_row.value) if exp_row and exp_row.value else 0.0
        if cached and cached.value and time.time() < exp:
            _token_cache.update(access_token=cached.value, expires_at=exp)
            session.rollback()
            return cached.value

        stored = rows.get("refresh_token")
        refresh_token = (stored.value if stored else None) or os.getenv("PORTAL_REFRESH_TOKEN", "").strip()
        if not refresh_token:
            raise AuthDead("no refresh_token stored - seed one via POST /auth/seed")

        data = _refresh_grant(refresh_token)
        access_token = data["access_token"]
        expires_at = time.time() + data.get("expires_in", 3600) - _ACCESS_SKEW

        _meta_put(session, rows, "refresh_token", data.get("refresh_token") or refresh_token)
        _meta_put(session, rows, "access_token", access_token)
        _meta_put(session, rows, "access_expires_at", str(expires_at))
        _meta_put(session, rows, "auth_alert_sent", "")
        session.commit()  # rotation is durable BEFORE the token is used

        _token_cache.update(access_token=access_token, expires_at=expires_at)
        return access_token
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def seed_refresh_token(refresh_token: str) -> dict:
    """Re-arm the chain from a browser-exported refresh_token. Verifies it before storing."""
    data = _refresh_grant(refresh_token.strip())
    session = get_session()
    try:
        session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": AUTH_LOCK_ID})
        rows = {m.key: m for m in session.query(Meta).filter(
            Meta.key.in_(_META_KEYS)).all()}
        expires_at = time.time() + data.get("expires_in", 3600) - _ACCESS_SKEW
        _meta_put(session, rows, "refresh_token", data.get("refresh_token") or refresh_token.strip())
        _meta_put(session, rows, "access_token", data["access_token"])
        _meta_put(session, rows, "access_expires_at", str(expires_at))
        _meta_put(session, rows, "auth_alert_sent", "")
        session.commit()
        _token_cache.update(access_token=data["access_token"], expires_at=expires_at)
        return {"status": "ok", "access_token_valid_until": expires_at}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

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
        log(f"Warning: Failed to fetch student profile: {e}")
    return {}

IST = timezone(timedelta(hours=5, minutes=30))

def parse_portal_deadline(raw) -> datetime | None:
    """job_availabilities.application_deadline is a naive local timestamp (23:59, 09:00
    patterns) - the portal is Indian, so read it as IST and hand back UTC."""
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(timezone.utc)

def fetch_availabilities(token: str, job_ids: list) -> dict:
    """job_availabilities holds the real application_deadline and the apply-button gate."""
    if not job_ids:
        return {}
    url = (f"{get_supabase_url()}/rest/v1/job_availabilities"
           f"?select=job_id,application_deadline,is_application_active,is_job_active,allow_student_applications"
           f"&job_id=in.({','.join(job_ids)})")
    headers = {"apikey": get_supabase_anon(), "Authorization": f"Bearer {token}"}
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url, headers=headers)
        if resp.status_code == 200:
            return {str(x["job_id"]): x for x in resp.json()}
        log(f"Warning: job_availabilities fetch failed (HTTP {resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        log(f"Warning: job_availabilities fetch failed: {e}")
    return {}

def is_student_eligible_for_job(job: dict, student: dict) -> tuple[bool, str]:
    """The students table stores branch/course as UUIDs (branch_id, course_id) and has no
    batch column - the batch is the year of expected_graduation_date. job_eligibilities
    holds the matching UUID lists, so every comparison here is on ids, not names."""
    if not student:
        return True, ""

    eligibilities = job.get("job_eligibilities") or []
    if not isinstance(eligibilities, list) or not eligibilities:
        return True, ""
    el = eligibilities[0] or {}

    # Course (B.E. / MCA / ...)
    course_id = el.get("course_id")
    if course_id and student.get("course_id") and course_id != student["course_id"]:
        return False, "course not eligible"

    # Batch = graduation year
    batches = [str(x) for x in (el.get("eligible_batches") or [])]
    grad_year = str(student.get("expected_graduation_date") or "")[:4]
    if batches and grad_year and grad_year not in batches:
        return False, f"Batch {grad_year} not in eligible batches {batches}"

    # Branch: eligible_branches, else the same list nested under course_eligible_branches
    branches = el.get("eligible_branches") or (el.get("course_eligible_branches") or {}).get("branches") or []
    branch_id = student.get("branch_id")
    if branches and branch_id and branch_id not in branches:
        return False, "Branch not eligible for this job"

    # CGPA
    min_gpa = el.get("min_gpa")
    if min_gpa is not None:
        try:
            if float(student.get("cgpa") or 0.0) < float(min_gpa):
                return False, f"CGPA {student.get('cgpa')} < min required {min_gpa}"
        except (TypeError, ValueError):
            pass

    # Class X / XII cutoffs
    for el_key, st_key, label in (("min_tenth_marks", "tenth_board_percent", "10th"),
                                  ("min_twelfth_marks", "twelfth_board_percent", "12th")):
        required = el.get(el_key)
        if required is not None:
            try:
                if float(student.get(st_key) or 0.0) < float(required):
                    return False, f"{label} {student.get(st_key)}% < min required {required}%"
            except (TypeError, ValueError):
                pass

    # Backlogs
    active = int(student.get("active_backlogs") or 0)
    ever = int(student.get("number_of_backlogs") or 0)
    if el.get("disallow_backlog_ever") and ever > 0:
        return False, f"job disallows any past backlog ({ever})"
    if el.get("allow_backlogs") is False and active > 0:
        return False, f"job disallows active backlogs ({active})"
    allowed_active = el.get("active_backlog_number")
    if allowed_active is not None and active > int(allowed_active):
        return False, f"active backlogs {active} > allowed {allowed_active}"

    # Gender (job stores lowercase)
    genders = [str(g).lower() for g in (el.get("genders") or [])]
    student_gender = str(student.get("gender") or "").lower()
    if genders and student_gender and student_gender not in genders:
        return False, f"gender {student_gender} not in {genders}"

    return True, ""

def fetch_eligible_jobs(apply_filter: bool = True) -> list:
    """
    Fetch live approved campus jobs, most recently approved first.
    apply_filter=False returns every posting with the skip reason attached (debugging).
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
            avail = fetch_availabilities(token, [
                str((m.get("jobs_posted") or {}).get("id") or m.get("job_id") or "")
                for m in mappings if (m.get("jobs_posted") or {}).get("id") or m.get("job_id")
            ])
            now = datetime.now(timezone.utc)
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

                # The apply button is gated by job_availabilities, not by the mapping status.
                av = avail.get(job_id) or {}
                deadline = parse_portal_deadline(av.get("application_deadline"))
                apply_open = not (av.get("allow_student_applications") is False
                                  or av.get("is_application_active") is False
                                  or av.get("is_job_active") is False)
                if eligible and not apply_open:
                    eligible, reason = False, "applications not open on the portal"
                elif eligible and deadline and deadline <= now:
                    eligible, reason = False, f"deadline passed ({deadline.isoformat()})"

                if not eligible:
                    log(f"Skipping ineligible job for student profile: {company_name} - {jp.get('title')} ({reason})")
                    if apply_filter:
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
                    "eligible": eligible,
                    "skip_reason": reason,
                    "apply_open": apply_open,
                    "approved_at": m.get("approved_at"),
                    "title": jp.get("title") or "Role",
                    "company": company_name,
                    "company_name": company_name,
                    "stipend": stipend_val,
                    "ctc": ctc_val,
                    "deadline": deadline.isoformat() if deadline else None,
                    "location": jp.get("location") or "",
                    "link": f"https://recruit.thapar.edu/student/jobs",
                    "raw_json": jp
                })
            return formatted_jobs
        else:
            log(f"Error fetching job_university_mappings (HTTP {resp.status_code}): {resp.text}")
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
            log(f"Error fetching applications (HTTP {resp.status_code}): {resp.text}")
            return set()
