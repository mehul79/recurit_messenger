import httpx
from portal import get_valid_access_token, get_supabase_url, get_supabase_anon

def check_eligibility():
    token = get_valid_access_token()
    headers = {
        "apikey": get_supabase_anon(),
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url_base = get_supabase_url()
    
    # 1. Fetch student info
    stu_url = f"{url_base}/rest/v1/students?select=*&email=eq.mgupta6_be23@thapar.edu"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(stu_url, headers=headers)
        student_cgpa = 8.17
        if resp.status_code == 200 and resp.json():
            student = resp.json()[0]
            print("=== STUDENT PROFILE ===")
            print(f"Name: {student.get('name')}")
            print(f"Email: {student.get('email')}")
            print(f"CGPA: {student.get('cgpa')}")
            print(f"Gender: {student.get('gender')}")
            student_cgpa = float(student.get('cgpa') or 8.17)

        # 2. Fetch approved job university mappings
        map_url = f"{url_base}/rest/v1/job_university_mappings?select=*,jobs_posted(*,companies(*),job_eligibilities(*))&status=eq.Approved&order=approved_at.desc.nullslast&limit=10"
        resp_m = client.get(map_url, headers=headers)
        if resp_m.status_code == 200:
            mappings = resp_m.json()
            print("\n" + "="*70)
            print(f"ELIGIBILITY AUDIT FOR YOUR PROFILE (CGPA: {student_cgpa}):")
            print("="*70)

            for i, m in enumerate(mappings, 1):
                jp = m.get("jobs_posted") or {}
                company_info = jp.get("companies") or {}
                company_name = company_info.get("name") if isinstance(company_info, dict) else "Company"
                title = jp.get("title") or "Role"

                el_list = jp.get("job_eligibilities") or []
                min_gpa = None
                allow_backlogs = True
                disallow_ever = False
                genders = []
                eligible_batches = []

                if el_list and isinstance(el_list, list) and len(el_list) > 0:
                    el = el_list[0]
                    min_gpa = float(el.get("min_gpa")) if el.get("min_gpa") is not None else None
                    allow_backlogs = el.get("allow_backlogs")
                    disallow_ever = el.get("disallow_backlog_ever")
                    genders = el.get("genders") or []
                    eligible_batches = el.get("eligible_batches") or []

                is_eligible = True
                reasons = []

                if min_gpa is not None and student_cgpa < min_gpa:
                    is_eligible = False
                    reasons.append(f"Min CGPA required is {min_gpa} (Your CGPA is {student_cgpa})")

                status_str = "ELIGIBLE [YES]" if is_eligible else "NOT ELIGIBLE [NO]"
                print(f"[{i}] {company_name} - {title}")
                print(f"    Status: {status_str}")
                if min_gpa is not None:
                    print(f"    Min CGPA Criteria: {min_gpa}")
                if reasons:
                    print(f"    Reason: {', '.join(reasons)}")
                print("-" * 70)

if __name__ == "__main__":
    check_eligibility()
