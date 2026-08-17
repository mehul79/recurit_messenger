import os
import httpx
from dotenv import load_dotenv

load_dotenv()

NTFY_TOPIC = os.getenv("NTFY_TOPIC", "thapar_job_alert_7979")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
TICK_SECRET = os.getenv("TICK_SECRET", "dev_tick_secret_123")
STUDENT_PORTAL_JOBS_URL = "https://recruit.thapar.edu/student/jobs"

_client = None

def get_http_client():
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.Client(timeout=20.0, follow_redirects=True)
    return _client

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
        return resp.status_code == 200
    except Exception as e:
        print(f"Error sending ntfy new job push: {e}")
        return False

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
        return resp.status_code == 200
    except Exception as e:
        print(f"Error sending ntfy checkpoint alarm: {e}")
        return False
