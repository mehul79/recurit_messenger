from state import get_session, Job

def get_most_recent_job_from_db():
    session = get_session()
    # Query top 5 most recent jobs
    jobs = session.query(Job).filter(Job.job_id != "test_job_123").order_by(Job.first_seen_at.desc()).limit(5).all()
    
    print("\n" + "="*70)
    print("MOST RECENT ELIGIBLE JOBS ON RECRUITSAGE:")
    print("="*70)

    for i, job in enumerate(jobs, 1):
        stipend_safe = str(job.stipend or "N/A").replace("₹", "INR ")
        ctc_safe = str(job.ctc or "N/A").replace("₹", "INR ")
        line = f"[{i}] {job.company} - {job.title} | Stipend: {stipend_safe} | CTC: {ctc_safe} | Location: {job.location or 'N/A'}"
        print(line.encode("ascii", errors="replace").decode("ascii"))
        print(f"    Link: {job.link}")
        print(f"    Deadline: {job.deadline}")
        print("-" * 70)

    session.close()

if __name__ == "__main__":
    get_most_recent_job_from_db()
