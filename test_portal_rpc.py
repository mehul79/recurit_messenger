from portal import fetch_eligible_jobs, fetch_applied_job_ids

def test_rpc():
    print("=== Testing Supabase RPC Calls ===")
    
    print("\n1. Calling get_eligible_jobs_rpc()...")
    jobs = fetch_eligible_jobs()
    print(f"Retrieved {len(jobs)} eligible job posting(s).")
    
    for i, j in enumerate(jobs[:5], 1):
        job_id = j.get("id") or j.get("job_id")
        company = j.get("company_name") or j.get("company") or "Company"
        title = j.get("job_title") or j.get("title") or "Role"
        deadline = j.get("deadline") or j.get("last_date") or "N/A"
        stipend = j.get("stipend") or "N/A"
        print(f" [{i}] {company} - {title} | Deadline: {deadline} | Stipend: {stipend} | ID: {job_id}".encode("ascii", errors="replace").decode("ascii"))


    print("\n2. Calling fetch_applied_job_ids()...")
    applied = fetch_applied_job_ids()
    print(f"Applied job IDs count: {len(applied)}")
    if applied:
        print(f"Sample applied IDs: {list(applied)[:5]}")

    print("\nALL RPC tests PASSED successfully!")

if __name__ == "__main__":
    test_rpc()
