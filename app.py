import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from state import get_session, Job, JobState, NotificationLog, init_db, Meta
from portal import fetch_eligible_jobs, fetch_applied_job_ids
from notify import send_new_job_push, send_checkpoint_alarm
from escalation import evaluate_next_checkpoint

load_dotenv()

TICK_SECRET = os.getenv("TICK_SECRET", "dev_tick_secret_123")

app = FastAPI(title="Thapar RecruitSage Watcher")

@app.on_event("startup")
def on_startup():
    try:
        init_db()
        print("Database schema initialized successfully.", flush=True)
    except Exception as e:
        print(f"Warning: Database initialization deferred: {e}", flush=True)

@app.get("/health")
@app.post("/health")
def health(secret: str = None):
    if secret == TICK_SECRET:
        return handle_tick(secret=secret)
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

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

        job_title = job_obj.title if job_obj else job
        company = job_obj.company if job_obj else ""

        return f"""
        <html>
            <head><title>Action Recorded</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 40px; background: #121212; color: #fff;">
                <h2 style="color: #4CAF50;">✓ Action Confirmed</h2>
                <p><strong>{company} · {job_title}</strong></p>
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
        print("Polling jobs from Supabase PostgREST...", flush=True)
        raw_jobs = fetch_eligible_jobs()
        summary["new_jobs_found"] = len(raw_jobs)
        print(f"Retrieved {len(raw_jobs)} job postings from Supabase.", flush=True)

        for rj in raw_jobs:
            job_id = str(rj.get("id") or rj.get("job_id") or "")
            if not job_id:
                continue

            company = rj.get("company_name") or rj.get("company") or "Company"
            title = rj.get("job_title") or rj.get("title") or "Role"
            stipend = str(rj.get("stipend") or "N/A")
            ctc = str(rj.get("ctc") or "")
            location = rj.get("location") or ""
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
                print(f"Sending ntfy alert for new job: {company} - {title}...", flush=True)
                success = send_new_job_push(job_dict)
                if success:
                    db_job.new_alert_sent = True
                    log_row = NotificationLog(
                        job_id=job_id,
                        sent_at=now,
                        kind="new_job",
                        message=f"Sent initial job alert for {company} · {title}"
                    )
                    session.add(log_row)
                    summary["new_pushes_sent"] += 1

        session.commit()

        print("Fetching student application status...", flush=True)
        applied_ids = fetch_applied_job_ids()
        print(f"Found {len(applied_ids)} applied job IDs.", flush=True)

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
                print(f"Sending ntfy checkpoint alarm ({checkpoint_due}) for: {job.company} - {job.title}...", flush=True)
                success = send_checkpoint_alarm(job_dict, checkpoint_due)
                if success:
                    updated_checkpoints = list(checkpoints_sent) + [checkpoint_due]
                    state.checkpoints_sent = updated_checkpoints
                    log_row = NotificationLog(
                        job_id=job.job_id,
                        sent_at=now,
                        kind=f"checkpoint_{checkpoint_due}",
                        message=f"Sent {checkpoint_due} deadline alarm for {job.company} · {job.title}"
                    )
                    session.add(log_row)
                    session.commit()
                    summary["checkpoints_fired"] += 1

        print(f"Tick execution complete. Summary: {summary}", flush=True)
        return {"status": "ok", "timestamp": now.isoformat(), "summary": summary}

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
