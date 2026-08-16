# Thapar RecruitSage — Eligible-Jobs Watcher + Deadline Alarm (ntfy-only)

## Context
`recruit.thapar.edu` ("RecruitSage") lists campus jobs; some the student isn't eligible for.
The student (mgupta6_be23@thapar.edu) wants an automated, **totally free ($0, no card, no account-ban risk)**
system that watches for eligible jobs and nags them before deadlines pass. WhatsApp was evaluated and
dropped: durable Cloud API use needs a Meta Business Portfolio, and real-world reports show even
low-volume, self-only test setups getting instantly banned/restricted (see research below) — unacceptable
risk for a system whose entire job is to reliably alert the student. **ntfy.sh alone** covers every
requirement (plain alerts, interactive action buttons, loud alarms) with zero account risk and zero cost.

### Why WhatsApp was dropped (recorded for future reference)
Researched via agent-reach web search over Meta's official docs + Reddit r/WhatsappBusinessAPI:
- Technically, a new/throwaway Facebook account is NOT required to match the sender phone number —
  Facebook account → Business Portfolio → Meta app → WABA → phone number are independently linked steps.
- BUT real accounts have been **banned within a day** for sending ~10 test messages to the developer's
  own number with zero automation/broadcast, and other WABAs get **permanently restricted the instant
  they're created**. New/thin business identities are exactly what Meta's anti-abuse system flags.
- Given the goal is a dependable personal alert system, that risk isn't worth it. **Decision: ntfy-only.**

### What recon established (already done, in-browser)
- Backend is **self-hosted Supabase** at `https://api.recruit.thapar.edu`
  - project ref `kqoqgzhjmmvvhgevyfph`; anon key is public in the JS bundle (`assets/index-*.js`).
  - Auth = Supabase GoTrue password grant: `POST /auth/v1/token?grant_type=password` with header `apikey: <anon>`, body `{email,password}` → returns `access_token` + rotating `refresh_token`.
  - Eligible jobs come from **server-side RPCs** — no client-side eligibility filtering needed. Relevant: `get_eligible_jobs_rpc`, `check_comprehensive_eligibility`, `get_student_dashboard_data`, `get_student_user_id`. Tables incl. `job_postings`, `job_eligibilities`, `job_applications`/`applications`, `students`, `companies`, `job_salaries`.
  - **Consequence: NO browser/Playwright needed at runtime.** The worker makes plain HTTPS calls to Supabase (PostgREST + GoTrue). Cheap and reliable on Render.
- The web login is behind **Cloudflare Turnstile** (managed mode; the automated browser could not clear it). Whether GoTrue *enforces* the captcha server-side on the password grant is the one **unverified risk** — see Step 0.

### Decisions locked with the user
- **Hosting:** Render **free** web service (Python, FastAPI).
- **DB:** **Aiven free-tier Postgres** (user is provisioning it). Accessed via `psycopg`/SQLAlchemy.
- **Notifications: ntfy.sh only.** No WhatsApp/Meta anywhere in the system.
- **Login to the portal:** try Supabase password grant first; fall back to one-time refresh-token export only if Turnstile is enforced server-side.
- **Scheduling:** Render free service sleeps when idle, so an external free pinger (**cron-job.org**, 1-min granularity) hits `/tick` to both wake the service and drive the state machine.
- **Approach: deterministic script, not an agent.** Every decision here is arithmetic on timestamps/booleans or an exact string match on which button was tapped — no natural-language interpretation or judgment call anywhere. A plain cron-driven `if/elif` state machine in Python is the correct tool; an LLM/agent would only add cost, latency, and non-determinism to something that must behave identically every time.

---

## Exact behavior spec (confirmed with the user)

1. **New eligible job appears** → send **one plain ntfy push, no buttons, no alarm priority**:
   `Company · Role` as title; body = stipend (and CTC if present), deadline, location (if present), direct job link.
2. **Deadline checkpoints** — at **T-2h, T-1.5h, T-1h, T-30m** before the deadline: if the job is not yet
   applied (per the portal) and not already acknowledged, send an **alarm-priority ntfy push with two
   action buttons**: `I don't wish to apply` and `Applying right now`. **This repeats at every checkpoint
   reached** while the job remains un-acknowledged and unapplied (so up to 4 separate alarms, not just one).
3. **Tapping either button stops the job's process entirely, permanently** — no more checkpoints, no
   T-20m re-check, nothing further, regardless of whether the student actually applies afterward:
   - `I don't wish to apply` → `opted_out = true`.
   - `Applying right now` → `acknowledged = true` (a distinct flag from opted_out, for the log/history, but
     behaviorally identical: silence forever for this job). Per the user's confirmed choice, silence is
     unconditional — the system does **not** re-check applied status at T-20m or resume alarming.
4. **Auto-detected as applied** (from the portal, independent of any button tap) at any point → also stops
   the job's process permanently (no point nagging about a job already applied to).
5. **Notification log** — every ntfy push sent (new-job alert or checkpoint alarm) is recorded in its own
   table: job, type, checkpoint label, timestamp, and the message body sent.

Net effect: the student sees a calm info push when a job appears, then up to 4 escalating alarm pushes
as a deadline nears if they've done nothing — and a single tap on either button silences that job for good.

---

## Architecture (one small FastAPI service + external cron)

```
cron-job.org --(every 1 min)--> POST /tick ----> [poll new jobs] + [checkpoint alarm loop]
ntfy action button --(tap)--> POST /act?job=&a=optout|ack&secret=…
                                   |
                        Aiven Postgres (state + log)
                                   |
             Supabase (read jobs + applied status)        ntfy.sh (all pushes)
```

- **`POST /tick`** — heartbeat; does the two jobs below. Guarded by `?secret=` so only cron-job.org can call it.
- **`POST /act`** — target of the two ntfy action buttons: `a=optout` or `a=ack`, both stop the job's process permanently; records which one was tapped and when.
- **`GET /health`** — trivial.

### `/tick` logic
1. **Poll for new jobs** (rate-limited via a `meta` last-poll timestamp, ~every 15 min):
   - Ensure a valid Supabase access token (refresh if near expiry).
   - Call the eligible-jobs RPC → upsert into `jobs` (id, title, company, link, posted_at, deadline, stipend, ctc, location, raw JSON).
   - Any row with `new_alert_sent = false` → send the plain info push (spec #1), mark `new_alert_sent = true`, insert a `notification_log` row.
2. **Checkpoint alarm loop:** for each job where `opted_out = false AND acknowledged = false AND applied = false` and `deadline` is in the future:
   - Refresh `applied` from Supabase (applications for this student); if now applied → set `applied = true`, stop (no further pushes for this job) — log nothing further.
   - Compute which of the four checkpoints (`2h`, `1.5h`, `1h`, `30m` before `deadline`) the current time has just reached that hasn't already been sent (`job_state.checkpoints_sent` — a small text array/set of labels already fired).
   - If a new checkpoint is reached: send the alarm-priority push with the two action buttons, add the label to `checkpoints_sent`, insert a `notification_log` row.
3. Button taps (via `/act`, independent of `/tick`): set `opted_out=true` or `acknowledged=true` immediately; insert a `notification_log` row noting which button was tapped.

### DB schema (Aiven Postgres)
- `jobs(job_id PK, title, company, link, posted_at, deadline, stipend, ctc, location, raw JSONB, first_seen_at, new_alert_sent bool)`
- `job_state(job_id PK→jobs, applied bool, opted_out bool, acknowledged bool, checkpoints_sent text[])`
- `notification_log(id PK, job_id→jobs, sent_at timestamptz, kind text, -- 'new_job' | 'checkpoint_2h' | ... | 'button_optout' | 'button_ack'
  message text)`
- `meta(key PK, value)` — last poll time, cached Supabase refresh token.

---

## Files (single Python service, kept lazy)
```
app.py            # FastAPI: /tick, /act, /health
portal.py         # Supabase login/refresh + get_eligible_jobs + applied-status
notify.py         # send_new_job_push(job), send_checkpoint_alarm(job, label) -> ntfy
state.py          # SQLAlchemy models + upsert/query helpers (Aiven Postgres) incl. notification_log writes
escalation.py     # pure logic: which checkpoint (if any) is newly due for a given (now, deadline, checkpoints_sent)
requirements.txt  # fastapi, uvicorn, httpx, sqlalchemy, psycopg[binary]
render.yaml       # Render free web service (build/start)
.env.example      # SUPABASE_URL, SUPABASE_ANON, PORTAL_EMAIL, PORTAL_PASSWORD,
                  # DATABASE_URL (Aiven), NTFY_TOPIC, PUBLIC_BASE_URL, TICK_SECRET
test_escalation.py# assert-based: correct checkpoint selection & no double-send; opt-out/ack both hard-stop; applied stops; new-job alert has no buttons
```
Secrets via Render env vars — nothing committed. `escalation.py` is pure functions over
(now, deadline, checkpoints_sent) so the state machine is unit-tested without network.

---

## Step 0 — VERIFY LOGIN FIRST (biggest risk, do before anything else)
Write a ~15-line `test_login.py` and have the user run it locally (`! python test_login.py`):
POST the password grant to `.../auth/v1/token?grant_type=password` with the anon key + their creds.
- **200 + tokens** → password login works headlessly. Proceed as planned.
- **400/403 with a captcha/"security" error** → GoTrue enforces Turnstile. Pivot auth to **one-time refresh-token export**: user logs in once in a real browser, copies the Supabase session (refresh_token) from `localStorage`, we store it as an env var and the worker refreshes it each run. Rest of the plan is unchanged.

## Build order
1. Step 0 login verification → pick auth path.
2. `portal.py`: token mgmt + `get_eligible_jobs()` (mapping title/company/link/posted_at/deadline/stipend/ctc/location from the RPC's real shape — introspect live with a curl once authenticated) + `is_applied(job_id)`.
3. `state.py` + schema (incl. `notification_log`) against the Aiven DB.
4. `escalation.py` + `test_escalation.py` (pure logic, no network).
5. `notify.py`: ntfy plain push + ntfy alarm-with-buttons push.
6. `app.py`: wire `/tick`, `/act`, `/health`.
7. `render.yaml` + `.env.example`; deploy to Render; set cron-job.org → `POST /tick?secret=…` every 1 min.

## Verification (end to end)
- **Login:** Step 0 returns 200 (or refresh-token path yields a usable access token).
- **Jobs:** run `/tick` locally against Aiven → `jobs` table populates with correct fields; a brand-new job triggers exactly one plain ntfy push (no buttons) with company/role/stipend/ctc/deadline/location/link, and one `notification_log` row.
- **Escalation (unit):** `python test_escalation.py` — each checkpoint fires exactly once; `I don't wish to apply` and `Applying right now` both hard-stop with no further pushes ever; auto-applied stops; no checkpoint fires after the deadline has passed.
- **Escalation (live smoke):** insert a fake job with `deadline = now + 2h5m`, drive `/tick` on a fast/injected clock → confirm the alarm+buttons push arrives at each checkpoint, tapping either button via `/act` fully silences it, and `notification_log` has one row per push plus one for the button tap.

## Prerequisites the user provides
- Aiven Postgres `DATABASE_URL`.
- ntfy app installed on phone, subscribed to a secret topic; per-topic DND-bypass + alarm/long sound enabled for urgent-priority pushes (I'll give exact steps).
- cron-job.org account (free) — I'll give the exact URL/schedule.
- Render account (free); `PUBLIC_BASE_URL` = the deployed Render URL (so ntfy action buttons can reach `/act`).

## Explicitly out of scope / deferred
- No WhatsApp / Meta anywhere (dropped due to account-ban risk found in research).
- No real PSTN phone call (not free); the ntfy alarm is the substitute for "ringing."
- No auto-applying to jobs — alerts only.
- No T-20m re-check after "Applying right now" — per the user's confirmed choice, a button tap is a permanent, unconditional stop.
