import os
import httpx
from dotenv import load_dotenv

load_dotenv()

NTFY_TOPIC = os.getenv("NTFY_TOPIC", "thapar_job_alert_7979")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
TICK_SECRET = os.getenv("TICK_SECRET", "dev_tick_secret_123")
STUDENT_PORTAL_JOBS_URL = "https://recruit.thapar.edu/student/jobs"

_client = None
LAST_ERROR = ""

def _fail(msg: str) -> bool:
    """Push failures used to vanish into a print on a server whose logs nobody reads."""
    global LAST_ERROR
    LAST_ERROR = msg
    print(f"ntfy send failed: {msg}", flush=True)
    return False

def get_http_client():
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.Client(timeout=20.0, follow_redirects=True)
    return _client

def send_auth_alert(detail: str) -> bool:
    """Portal login chain is dead -> the watcher is blind. Say so loudly, once."""
    body = (
        "The watcher can no longer log in to the portal, so NO job alerts are being sent.\n\n"
        "Fix: log in at recruit.thapar.edu in a browser, copy refresh_token from the "
        "sb-*-auth-token localStorage entry, then POST it to:\n"
        f"{PUBLIC_BASE_URL}/auth/seed?secret={TICK_SECRET}&refresh_token=<token>\n\n"
        f"Detail: {detail}"
    )
    try:
        resp = get_http_client().post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=body.encode("utf-8"),
            headers={"Title": "RecruitSage AUTH BROKEN - action needed",
                     "Priority": "urgent", "Tags": "rotating_light"},
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Error sending ntfy auth alert: {e}")
        return False

def send_new_job_push(job: dict) -> bool:
    """
    Spec #1: New eligible job appears -> send one plain ntfy push, no buttons, no alarm priority.
    """
    company = str(job.get("company", "Company"))
    title = str(job.get("title", "Role"))
    stipend = str(job.get("stipend", "N/A"))
    ctc = str(job.get("ctc", ""))
    deadline = str(job.get("deadline", "N/A"))
    location = str(job.get("location", ""))
    link = STUDENT_PORTAL_JOBS_URL

    body_lines = [
        f"Stipend: {stipend}",
    ]
    if ctc:
        body_lines.append(f"CTC: {ctc}")
    body_lines.append(f"Deadline: {deadline}")
    if location:
        body_lines.append(f"Location: {location}")
    body_lines.append(f"Link: {link}")

    body = "\n".join(body_lines)
    header_title = f"New Job: {company} - {title}".encode("latin-1", errors="replace").decode("latin-1")

    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    headers = {
        "Title": header_title,
        "Priority": "default",
        "Tags": "briefcase",
        "Click": link
    }

    try:
        client = get_http_client()
        resp = client.post(url, data=body.encode("utf-8"), headers=headers)
        if resp.status_code != 200:
            return _fail(f"new_job HTTP {resp.status_code}: {resp.text[:200]}")
        return True
    except Exception as e:
        return _fail(f"new_job {type(e).__name__}: {e}")

def send_checkpoint_alarm(job: dict, label: str) -> bool:
    """
    Spec #2: Deadline checkpoint (T-2h, T-1.5h, T-1h, T-30m) -> send alarm-priority ntfy push
    with action buttons: 'I don't wish to apply' and 'Applying right now'.
    """
    job_id = str(job.get("job_id", ""))
    company = str(job.get("company", "Company"))
    title = str(job.get("title", "Role"))
    stipend = str(job.get("stipend", "N/A"))
    ctc = str(job.get("ctc", ""))
    deadline = str(job.get("deadline", "N/A"))
    link = STUDENT_PORTAL_JOBS_URL

    body_lines = [
        f"⚠️ Deadline approaching in ~{label}!",
        f"Stipend: {stipend}",
    ]
    if ctc:
        body_lines.append(f"CTC: {ctc}")
    body_lines.append(f"Deadline: {deadline}")
    body_lines.append(f"Link: {link}")

    body = "\n".join(body_lines)

    optout_url = f"{PUBLIC_BASE_URL}/act?job={job_id}&a=optout&secret={TICK_SECRET}"
    ack_url = f"{PUBLIC_BASE_URL}/act?job={job_id}&a=ack&secret={TICK_SECRET}"

    action_header = f"http, I don't wish to apply, {optout_url}, method=POST; http, Applying right now, {ack_url}, method=POST"
    header_title = f"URGENT ({label} left): {company} - {title}".encode("latin-1", errors="replace").decode("latin-1")

    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    headers = {
        "Title": header_title,
        "Priority": "urgent",
        "Tags": "warning,alarm_clock",
        "Click": link,
        "Actions": action_header
    }

    try:
        client = get_http_client()
        resp = client.post(url, data=body.encode("utf-8"), headers=headers)
        if resp.status_code != 200:
            return _fail(f"checkpoint HTTP {resp.status_code}: {resp.text[:200]}")
        return True
    except Exception as e:
        return _fail(f"checkpoint {type(e).__name__}: {e}")
