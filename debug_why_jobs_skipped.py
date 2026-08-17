import httpx
from portal import get_valid_access_token, fetch_student_profile, is_student_eligible_for_job, get_supabase_url, get_supabase_anon

def debug_jobs():
    token = get_valid_access_token()
    student = fetch_student_profile(token)
    
    print("=== STUDENT PROFILE FETCHED BY SYSTEM ===")
    print(student)

    url = f"{get_supabase_url()}/rest/v1/job_university_mappings?select=*,jobs_posted(*,companies(*),job_salaries(*),job_eligibilities(*))&status=eq.Approved&order=approved_at.desc.nullslast&limit=50"
    headers = {
        "apikey": get_supabase_anon(),
        "Authorization": f"Bearer {token}"
    }

    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
        if resp.status_code == 200:
            mappings = resp.json()
            print(f"\nTotal Approved University Mappings Fetched: {len(mappings)}")
            print("="*80)

            for i, m in enumerate(mappings, 1):
                jp = m.get("jobs_posted") or {}
                company_info = jp.get("companies") or {}
                company_name = company_info.get("name") if isinstance(company_info, dict) else "Company"
                title = jp.get("title") or "Role"

                eligible, reason = is_student_eligible_for_job(jp, student)
                status_str = "PASSED [KEEP]" if eligible else f"SKIPPED [{reason}]"

                print(f"[{i}] {company_name} - {title}")
                print(f"    Approved At: {m.get('approved_at')}")
                print(f"    Eligibility Result: {status_str}")
                el = (jp.get("job_eligibilities") or [{}])[0]
                print(f"    Job Eligibilities -> Min GPA: {el.get('min_gpa')}, Batches: {el.get('eligible_batches')}, Branches: {el.get('eligible_branches') or el.get('branches')}")
                print("-" * 80)

if __name__ == "__main__":
    debug_jobs()
