import httpx
from portal import get_valid_access_token, get_supabase_url, get_supabase_anon

def search_zepto_akamai():
    token = get_valid_access_token()
    headers = {
        "apikey": get_supabase_anon(),
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url_base = get_supabase_url()
    
    map_url = f"{url_base}/rest/v1/job_university_mappings?select=*,jobs_posted(*,companies(*),job_salaries(*),job_eligibilities(*))&status=eq.Approved&order=approved_at.desc.nullslast&limit=50"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(map_url, headers=headers)
        if resp.status_code == 200:
            mappings = resp.json()
            targets = ["zepto", "akamai"]
            print("\n" + "="*70)
            print("SEARCH RESULTS FOR ZEPTO & AKAMAI:")
            print("="*70)

            found_count = 0
            for m in mappings:
                jp = m.get("jobs_posted") or {}
                company_info = jp.get("companies") or {}
                company_name = company_info.get("name") if isinstance(company_info, dict) else "Company"
                title = jp.get("title") or "Role"
                approved_at = m.get("approved_at") or m.get("created_at") or "N/A"
                deadline = jp.get("application_deadline") or "N/A"
                job_id = jp.get("id")

                salaries = jp.get("job_salaries") or []
                stipend = "N/A"
                ctc = "N/A"
                if salaries and isinstance(salaries, list) and len(salaries) > 0:
                    sal = salaries[0]
                    if sal.get("stipend"):
                        stipend = f"INR {sal.get('stipend'):,}/pm"
                    if sal.get("ctc"):
                        ctc = f"INR {sal.get('ctc'):,}"

                el_list = jp.get("job_eligibilities") or []
                min_gpa = "None"
                if el_list and isinstance(el_list, list) and len(el_list) > 0:
                    min_gpa = str(el_list[0].get("min_gpa", "None"))

                if any(t in company_name.lower() for t in targets):
                    found_count += 1
                    print(f"[{found_count}] COMPANY: {company_name}")
                    print(f"    Role / Title:       {title}")
                    print(f"    Approved Date:      {approved_at}")
                    print(f"    Application Deadline: {deadline}")
                    print(f"    Stipend:            {stipend}")
                    print(f"    CTC Package:        {ctc}")
                    print(f"    Min CGPA Criteria:  {min_gpa}")
                    print(f"    Job ID:             {job_id}")
                    print("-" * 70)

            print(f"\nTotal Matching Postings Found: {found_count}")

if __name__ == "__main__":
    search_zepto_akamai()
