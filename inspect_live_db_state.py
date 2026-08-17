from state import get_session, Job, JobState, NotificationLog
from datetime import datetime, timezone

def inspect_db():
    session = get_session()
    now = datetime.now(timezone.utc)
    print("=== Current Database Job States ===")
    
    jobs = session.query(Job).all()
    print(f"Total Jobs in Database: {len(jobs)}")
    
    applied_count = 0
    optout_count = 0
    ack_count = 0
    new_alert_sent_count = 0
    checkpoints_due_count = 0

    for j in jobs:
        state = j.state
        if j.new_alert_sent:
            new_alert_sent_count += 1
        if state:
            if state.applied:
                applied_count += 1
            if state.opted_out:
                optout_count += 1
            if state.acknowledged:
                ack_count += 1
                
        print(f"Job: {j.company} - {j.title}")
        print(f"  ID: {j.job_id}")
        print(f"  Deadline: {j.deadline}")
        print(f"  New Alert Sent: {j.new_alert_sent}")
        if state:
            print(f"  State -> Applied: {state.applied} | OptedOut: {state.opted_out} | Ack: {state.acknowledged} | CheckpointsSent: {state.checkpoints_sent}")

    print("\nSummary:")
    print(f"  - Jobs with New Alert Sent: {new_alert_sent_count}/{len(jobs)}")
    print(f"  - Jobs Auto-Detected as Applied: {applied_count}")
    print(f"  - Jobs Opted Out / Acked: {optout_count + ack_count}")
    session.close()

if __name__ == "__main__":
    inspect_db()
