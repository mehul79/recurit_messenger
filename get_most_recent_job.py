import httpx
from portal import get_valid_access_token, SUPABASE_URL, SUPABASE_ANON

def get_recent():
    token = get_valid_access_token()
    headers = {
        "apikey": SUPABASE_ANON,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = f"{SUPABASE_URL}/rest/v1/jobs_posted?select=*,companies(*),job_salaries(*)&order=created_at.desc&limit=5"
    
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
        if resp.status_code == 200:
            jobs = resp.json()
            print(f"Total jobs fetched: {len(jobs)}")
            print("="*60)
            for i, j in enumerate(jobs, 1):
                company_info = j.get("companies") or {}
                company_name = company_info.get("name") if isinstance(company_info, dict) else "Company"
                title = j.get("title") or "Role"
                created_at = j.get("created_at") or "N/A"
                deadline = j.get("application_deadline") or "N/A"
                location = j.get("location") or "N/A"
                job_id = j.get("id")

                salaries = j.get("job_salaries") or []
                stipend = "N/A"
                ctc = "N/A"
                if salaries and isinstance(salaries, list) and len(salaries) > 0:
                    sal = salaries[0]
                    if sal.get("stipend"):
                        stipend = f"₹{sal.get('stipend'):,}/pm"
                    if sal.get("ctc"):
                        ctc = f"₹{sal.get('ctc'):,}"

                print(f"[{i}] MOST RECENT JOB #{i}")
                print(f"    Company: {company_name}")
                print(f"    Title: {title}")
                print(f"    Posted At (created_at): {created_at}")
                print(f"    Deadline: {deadline}")
                print(f"    Location: {location}")
                print(f"    Stipend: {stipend}")
                print(f"    CTC: {ctc}")
                print(f"    Job ID: {job_id}")
                print("="*60)
        else:
            print("Error:", resp.status_code, resp.text)

if __name__ == "__main__":
    get_recent()
