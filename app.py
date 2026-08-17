import os
import re
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from state import get_session, Job, JobState, NotificationLog, init_db, Meta
from portal import fetch_eligible_jobs, fetch_applied_job_ids, seed_refresh_token, AuthDead
import notify
from notify import send_new_job_push, send_checkpoint_alarm, send_auth_alert
from escalation import evaluate_next_checkpoint

load_dotenv()

TICK_SECRET = os.getenv("TICK_SECRET", "dev_tick_secret_123")

app = FastAPI(title="Thapar RecruitSage Watcher")

def sanitize_text(text: str) -> str:
    if not text:
        return ""
    # Replace narrow non-breaking spaces (\u202f, \xa0) and non-standard whitespace with plain spaces
    cleaned = re.sub(r'[\u202f\xa0\u200b\u200e\u200f]', ' ', str(text))
    return cleaned.strip()

def safe_log_print(msg: str):
    try:
        print(msg.encode("ascii", errors="replace").decode("ascii"), flush=True)
    except Exception:
        pass

@app.on_event("startup")
def on_startup():
    try:
        init_db()
        safe_log_print("Database schema initialized successfully.")
    except Exception as e:
        safe_log_print(f"Warning: Database initialization deferred: {e}")

@app.get("/health")
@app.post("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/auth/seed", response_class=HTMLResponse)
@app.post("/auth/seed", response_class=HTMLResponse)
def auth_seed(refresh_token: str = Query(...), secret: str = Query(...)):
    """Re-arm the token chain from a browser-exported refresh_token."""
    if secret != TICK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid tick secret")
    try:
        seed_refresh_token(refresh_token)
    except AuthDead as e:
        raise HTTPException(status_code=400, detail=f"Token rejected by portal: {e}")
    return "<h2>Token accepted. Watcher is live again.</h2>"

@app.get("/jobs")
def list_jobs(secret: str = Query(...), limit: int = 10, all: bool = False):
    """Most recently approved postings the watcher can see, newest first.
    all=true also returns the ones filtered out, with the reason."""
    if secret != TICK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid tick secret")
    try:
        jobs = fetch_eligible_jobs(apply_filter=not all)
        applied = fetch_applied_job_ids()
    except AuthDead as e:
        _on_auth_dead(e)
        raise HTTPException(status_code=503, detail=f"Portal auth broken, re-seed via /auth/seed: {e}")

    session = get_session()
    try:
        out = []
        for j in jobs[:limit]:
            state = session.query(JobState).filter(JobState.job_id == j["job_id"]).first()
            out.append({
                "job_id": j["job_id"],
                "company": sanitize_text(j["company"]),
                "title": sanitize_text(j["title"]),
                "stipend": j["stipend"],
                "ctc": j["ctc"],
                "deadline": j["deadline"],
                "approved_at": j.get("approved_at"),
                "location": sanitize_text(j["location"]),
                "eligible": j.get("eligible", True),
                "skip_reason": j.get("skip_reason", ""),
                "applied": j["job_id"] in applied,
                "alerted": bool(session.query(Job).filter(
                    Job.job_id == j["job_id"], Job.new_alert_sent.is_(True)).first()),
                "checkpoints_sent": (state.checkpoints_sent if state else []) or [],
                "silenced": bool(state and (state.opted_out or state.acknowledged)),
            })
        return {"count": len(out), "jobs": out}
    finally:
        session.close()

def _on_auth_dead(err: Exception):
    """Alert once per outage; the flag is cleared by the next successful refresh."""
    session = get_session()
    try:
        row = session.query(Meta).filter(Meta.key == "auth_alert_sent").first()
        if row and row.value:
            return
        if send_auth_alert(str(err)):
            if row:
                row.value = "1"
            else:
                session.add(Meta(key="auth_alert_sent", value="1"))
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

@app.get("/act", response_class=HTMLResponse)
@app.post("/act", response_class=HTMLResponse)
def handle_action(
    job: str = Query(...),
    a: str = Query(...),
    secret: str = Query(...)
):
    if secret != TICK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid tick secret")
    
    if a not in ("optout", "ack"):
        raise HTTPException(status_code=400, detail="Invalid action type")

    session = get_session()
    try:
        job_obj = session.query(Job).filter(Job.job_id == job).first()
        if not job_obj:
            job_obj = Job(
                job_id=job,
                title="Unknown Job",
                company="Unknown Company",
                link="https://recruit.thapar.edu",
                first_seen_at=datetime.now(timezone.utc),
                new_alert_sent=True
            )
            session.add(job_obj)
            session.flush()

        state_obj = session.query(JobState).filter(JobState.job_id == job).first()
        if not state_obj:
            state_obj = JobState(job_id=job)
            session.add(state_obj)

        action_kind = ""
        action_text = ""

        if a == "optout":
            state_obj.opted_out = True
            action_kind = "button_optout"
            action_text = "Opted Out (silenced permanently)"
        elif a == "ack":
            state_obj.acknowledged = True
            action_kind = "button_ack"
            action_text = "Acknowledged (Applying right now - silenced permanently)"

        log_entry = NotificationLog(
            job_id=job,
            sent_at=datetime.now(timezone.utc),
            kind=action_kind,
            message=f"User tapped action button: {action_text}"
        )
        session.add(log_entry)
        session.commit()

        job_title = sanitize_text(job_obj.title) if job_obj else job
        company = sanitize_text(job_obj.company) if job_obj else ""

        return f"""
        <html>
            <head><title>Action Recorded</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 40px; background: #121212; color: #fff;">
                <h2 style="color: #4CAF50;">✓ Action Confirmed</h2>
                <p><strong>{company} - {job_title}</strong></p>
                <p>Status: {action_text}</p>
                <p style="color: #aaa; font-size: 0.9em;">You will receive no further alarms for this job posting.</p>
            </body>
        </html>
        """
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/tick")
@app.post("/tick")
def handle_tick(secret: str = Query(...)):
    if secret != TICK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid tick secret")

    now = datetime.now(timezone.utc)
    session = get_session()
    summary = {
        "new_jobs_found": 0,
        "new_pushes_sent": 0,
        "checkpoints_fired": 0,
        "jobs_checked": 0
    }

    try:
        safe_log_print("Polling jobs from Supabase PostgREST...")
        raw_jobs = fetch_eligible_jobs()
        summary["new_jobs_found"] = len(raw_jobs)
        safe_log_print(f"Retrieved {len(raw_jobs)} job postings from Supabase.")

        for rj in raw_jobs:
            job_id = str(rj.get("id") or rj.get("job_id") or "")
            if not job_id:
                continue

            company = sanitize_text(rj.get("company_name") or rj.get("company") or "Company")
            title = sanitize_text(rj.get("title") or rj.get("job_title") or "Role")
            stipend = sanitize_text(str(rj.get("stipend") or "N/A"))
            ctc = sanitize_text(str(rj.get("ctc") or ""))
            location = sanitize_text(rj.get("location") or "")
            link = f"https://recruit.thapar.edu/job/{job_id}"

            deadline_dt = None
            raw_deadline = rj.get("deadline") or rj.get("last_date")
            if raw_deadline:
                try:
                    deadline_dt = datetime.fromisoformat(str(raw_deadline).replace("Z", "+00:00"))
                except Exception:
                    pass

            db_job = session.query(Job).filter(Job.job_id == job_id).first()
            if not db_job:
                db_job = Job(
                    job_id=job_id,
                    title=title,
                    company=company,
                    link=link,
                    deadline=deadline_dt,
                    stipend=stipend,
                    ctc=ctc,
                    location=location,
                    raw_json=rj,
                    first_seen_at=now,
                    new_alert_sent=False
                )
                session.add(db_job)
                session.flush()

                db_state = JobState(job_id=job_id, checkpoints_sent=[])
                session.add(db_state)
            else:
                # Deadlines and stipends get edited on the portal after posting, so keep
                # the row in sync - otherwise a stale deadline silently kills the alarms.
                db_job.deadline = deadline_dt
                db_job.stipend = stipend
                db_job.ctc = ctc
                db_job.location = location
                db_job.title = title
                db_job.company = company

            if not db_job.new_alert_sent:
                job_dict = {
                    "job_id": job_id,
                    "title": title,
                    "company": company,
                    "stipend": stipend,
                    "ctc": ctc,
                    "deadline": str(raw_deadline or "N/A"),
                    "location": location,
                    "link": link
                }
                safe_log_print(f"Sending ntfy alert for new job: {company} - {title}...")
                success = send_new_job_push(job_dict)
                if success:
                    db_job.new_alert_sent = True
                    log_row = NotificationLog(
                        job_id=job_id,
                        sent_at=now,
                        kind="new_job",
                        message=f"Sent initial job alert for {company} - {title}"
                    )
                    session.add(log_row)
                    summary["new_pushes_sent"] += 1

        session.commit()

        safe_log_print("Fetching student application status...")
        applied_ids = fetch_applied_job_ids()
        safe_log_print(f"Found {len(applied_ids)} applied job IDs.")

        active_jobs = session.query(Job).join(JobState).all()
        summary["jobs_checked"] = len(active_jobs)

        for job in active_jobs:
            state = job.state
            if not state:
                continue

            if state.opted_out or state.acknowledged or state.applied:
                continue

            if job.job_id in applied_ids:
                state.applied = True
                session.commit()
                continue

            if not job.deadline:
                continue

            checkpoints_sent = state.checkpoints_sent or []
            checkpoint_due = evaluate_next_checkpoint(now, job.deadline, checkpoints_sent)

            if checkpoint_due:
                job_dict = {
                    "job_id": job.job_id,
                    "title": job.title,
                    "company": job.company,
                    "stipend": job.stipend,
                    "ctc": job.ctc,
                    "deadline": str(job.deadline),
                    "location": job.location,
                    "link": job.link
                }
                safe_log_print(f"Sending ntfy checkpoint alarm ({checkpoint_due}) for: {job.company} - {job.title}...")
                success = send_checkpoint_alarm(job_dict, checkpoint_due)
                if success:
                    updated_checkpoints = list(checkpoints_sent) + [checkpoint_due]
                    state.checkpoints_sent = updated_checkpoints
                    log_row = NotificationLog(
                        job_id=job.job_id,
                        sent_at=now,
                        kind=f"checkpoint_{checkpoint_due}",
                        message=f"Sent {checkpoint_due} deadline alarm for {job.company} - {job.title}"
                    )
                    session.add(log_row)
                    session.commit()
                    summary["checkpoints_fired"] += 1

        safe_log_print(f"Tick execution complete. Summary: {summary}")
        if notify.LAST_ERROR:
            summary["ntfy_error"] = notify.LAST_ERROR
        summary["ntfy_topic"] = notify.NTFY_TOPIC
        summary["ntfy_auth"] = bool(notify.NTFY_TOKEN)
        return {"status": "ok", "timestamp": now.isoformat(), "summary": summary}

    except AuthDead as e:
        session.rollback()
        safe_log_print(f"AUTH DEAD: {e}")
        _on_auth_dead(e)
        raise HTTPException(status_code=503, detail=f"Portal auth broken, re-seed via /auth/seed: {e}")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
