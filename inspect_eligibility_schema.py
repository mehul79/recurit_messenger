import httpx
from state import get_session, Meta
from portal import get_supabase_url, get_supabase_anon, update_stored_tokens

def inspect_schema():
    session = get_session()
    meta_row = session.query(Meta).filter(Meta.key == "refresh_token").first()
    db_refresh_token = meta_row.value if meta_row else None
    session.close()

    url_base = get_supabase_url()
    anon_key = get_supabase_anon()

    url = f"{url_base}/auth/v1/token?grant_type=refresh_token"
    headers = {"apikey": anon_key, "Content-Type": "application/json"}

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, headers=headers, json={"refresh_token": db_refresh_token})
        if resp.status_code != 200:
            print("Token refresh error:", resp.status_code, resp.text)
            return
        
        data = resp.json()
        token = data.get("access_token")
        new_ref = data.get("refresh_token")
        if new_ref:
            update_stored_tokens(token, new_ref)

        headers_auth = {
            "apikey": anon_key,
            "Authorization": f"Bearer {token}"
        }

        # 1. Inspect Student Details
        stu_resp = client.get(f"{url_base}/rest/v1/students?select=*&email=eq.mgupta6_be23@thapar.edu", headers=headers_auth)
        print("=== STUDENT RECORD ===")
        if stu_resp.status_code == 200 and stu_resp.json():
            student = stu_resp.json()[0]
            for k, v in student.items():
                print(f"  {k}: {v}")

        # 2. Inspect Zepto job eligibility specifically
        job_resp = client.get(f"{url_base}/rest/v1/jobs_posted?select=*,companies(*),job_eligibilities(*),job_university_mappings(*)&id=eq.e1942047-8e82-4b62-8bb4-e5a6d24f812a", headers=headers_auth)
        print("\n=== ZEPTO JOB RECORD ===")
        if job_resp.status_code == 200 and job_resp.json():
            zepto = job_resp.json()[0]
            print(f"Title: {zepto.get('title')}")
            print(f"Deadline: {zepto.get('application_deadline')}")
            print(f"Job Eligibilities Raw: {zepto.get('job_eligibilities')}")
            print(f"Job Mappings Raw: {zepto.get('job_university_mappings')}")

        # 3. Inspect Akamai job eligibility
        akamai_resp = client.get(f"{url_base}/rest/v1/jobs_posted?select=*,companies(*),job_eligibilities(*),job_university_mappings(*)&id=eq.97c85300-e9c2-413a-bd5e-18883761b04e", headers=headers_auth)
        print("\n=== AKAMAI JOB RECORD ===")
        if akamai_resp.status_code == 200 and akamai_resp.json():
            akamai = akamai_resp.json()[0]
            print(f"Title: {akamai.get('title')}")
            print(f"Deadline: {akamai.get('application_deadline')}")
            print(f"Job Eligibilities Raw: {akamai.get('job_eligibilities')}")
            print(f"Job Mappings Raw: {akamai.get('job_university_mappings')}")

if __name__ == "__main__":
    inspect_schema()
