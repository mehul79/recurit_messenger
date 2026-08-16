# 🎓 Thapar RecruitSage — Eligible-Jobs Watcher & Deadline Alarm

[![Python 3.12](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![ntfy](https://img.shields.io/badge/Notifications-ntfy.sh-orange.svg)](https://ntfy.sh)

An automated, $0-cost personal alerting system for **RecruitSage** (`recruit.thapar.edu`). It watches for newly posted eligible campus jobs and sends escalating **ntfy** alarms before application deadlines pass, complete with interactive action buttons to silence notifications on demand.

---

## 🌟 Key Features

- ⚡ **Direct Supabase PostgREST & GoTrue API**: Operates completely headlessly via plain HTTPS requests — zero browser or Playwright overhead at runtime.
- 🔔 **Instant New Job Alerts**: Sends a clean `ntfy` push notification the moment a new eligible job is posted (includes company, role, stipend, CTC, location, and direct link).
- 🚨 **Escalating Deadline Alarms**: Fires urgent-priority alarms at 4 deadline checkpoints (`T-2h`, `T-1.5h`, `T-1h`, `T-30m`) if you haven't applied yet.
- 🔘 **Interactive Action Buttons**: Push notifications include two tap actions:
  - `I don't wish to apply` 🛑
  - `Applying right now` ✅
  - *Tapping either button silences further alarms for that specific job permanently.*
- 🛡️ **Auto-Detection**: Automatically detects when a job is marked as applied on the portal and silences alerts.
- 🗄️ **Persistent State Machine**: Uses PostgreSQL (Aiven / Supabase) to track job states, checkpoint progression, and full notification history.
- ☁️ **Free Tier Deployment**: Tailored for **Render** free tier with **cron-job.org** driving the `/tick` heartbeat.

---

## 📐 Architecture & Data Flow

```
cron-job.org --(every 1 min)--> POST /tick?secret=... (FastAPI / app.py)
                                           |
                    +----------------------+----------------------+
                    |                                             |
   Supabase API & RPCs (portal.py)                    ntfy.sh (notify.py)
   • PostgREST /jobs_posted & /applications           • Plain info pushes
   • GoTrue Auth refresh                              • Urgent priority alarms
                    |                                 • Interactive action buttons
     Aiven Postgres (state.py)
     • jobs, job_state, notification_log, meta
```

---

## 🛠️ Project Structure

```
.
├── app.py                   # FastAPI service: /health, /act, /tick
├── portal.py                # Supabase GoTrue auth & PostgREST query client
├── escalation.py            # Checkpoint evaluation logic (T-2h, T-1.5h, T-1h, T-30m)
├── notify.py                # ntfy.sh alert builder (info pushes & alarm pushes with buttons)
├── state.py                 # SQLAlchemy database models & PostgreSQL connection engine
├── test_escalation.py       # Unit tests for checkpoint escalation logic
├── test_app_endpoints.py    # Route tests for FastAPI application endpoints
├── render.yaml              # Render web service deployment manifest
├── requirements.txt         # Project Python dependencies
└── .env.example             # Template for required environment variables
```

---

## 🚀 Quick Start (Local Setup)

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/mehul79/recruit_messenger.git
cd recruit_messenger
python -m venv .venv
.\.venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file based on `.env.example`:

```env
SUPABASE_URL=https://api.recruit.thapar.edu
SUPABASE_ANON=your_supabase_anon_key
PORTAL_EMAIL=your_email@thapar.edu
PORTAL_PASSWORD=your_password
DATABASE_URL=postgresql://user:pass@host:port/dbname?sslmode=require
NTFY_TOPIC=thapar_job_alert_7979
PUBLIC_BASE_URL=http://localhost:8000
TICK_SECRET=dev_tick_secret_123
PORTAL_REFRESH_TOKEN=your_refresh_token
```

### 3. Run Database Migrations & Verification

```bash
python test_db.py
python test_portal_rpc.py
```

### 4. Start the Application Locally

```bash
uvicorn app:app --reload --port 8000
```

Trigger a heartbeat tick manually:
```bash
curl -X POST "http://localhost:8000/tick?secret=dev_tick_secret_123"
```

---

## ☁️ Deployment (Render + cron-job.org)

1. **Deploy to Render**:
   - Create a new Web Service on [Render](https://render.com/).
   - Connect this GitHub repository (`mehul79/recruit_messenger`).
   - Render will automatically detect `render.yaml`.
   - Add environment variables (`DATABASE_URL`, `SUPABASE_ANON`, `PORTAL_EMAIL`, `PORTAL_PASSWORD`, `NTFY_TOPIC`, `PUBLIC_BASE_URL`, `PORTAL_REFRESH_TOKEN`).

2. **Configure Cron Heartbeat**:
   - Create a free account on [cron-job.org](https://cron-job.org/).
   - Add a cron job running **every 1 minute**:
     `POST https://<your-render-app>.onrender.com/tick?secret=<YOUR_TICK_SECRET>`

---

## 📱 Mobile App Setup (ntfy)

1. Download **ntfy** on [iOS](https://apps.apple.com/app/ntfy/id1625396386) or [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy).
2. Tap **+** and subscribe to your topic (e.g., `thapar_job_alert_7979`).
3. Enable notification sounds and high-priority DND bypass permissions for urgent deadline alarms.

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
