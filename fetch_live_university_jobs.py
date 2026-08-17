import os
import httpx
from state import get_session, Meta
from portal import get_supabase_url, get_supabase_anon, update_stored_tokens

def fetch_live_jobs():
    token_to_use = "sbl23k4yzrev"
    url_base = get_supabase_url()
    anon_key = get_supabase_anon()

    url = f"{url_base}/auth/v1/token?grant_type=refresh_token"
    headers = {"apikey": anon_key, "Content-Type": "application/json"}
    
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, headers=headers, json={"refresh_token": token_to_use})
        print(f"Auth Refresh Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            access_token = data.get("access_token")
            new_ref = data.get("refresh_token")
            if new_ref:
                update_stored_tokens(access_token, new_ref)
                print("Updated DB meta table with new refresh token!")

            auth_headers = {"apikey": anon_key, "Authorization": f"Bearer {access_token}"}
            
            # Query job_university_mappings
            map_url = f"{url_base}/rest/v1/job_university_mappings?select=*,jobs_posted(*,companies(*),job_salaries(*))&status=eq.Approved&order=approved_at.desc.nullslast&limit=30"
            map_resp = client.get(map_url, headers=auth_headers)
            print(f"Approved Mappings Fetch Status: {map_resp.status_code}")
            if map_resp.status_code == 200:
                mappings = map_resp.json()
                print("\n" + "="*70)
                print(f"LIVE APPROVED CAMPUS JOBS FOR YOUR PROFILE ({len(mappings)} Total):")
                print("="*70)

                for i, m in enumerate(mappings, 1):
                    jp = m.get("jobs_posted") or {}
                    company_info = jp.get("companies") or {}
                    company_name = company_info.get("name") if isinstance(company_info, dict) else "Company"
                    title = jp.get("title") or "Role"
                    approved_at = m.get("approved_at") or m.get("created_at") or "N/A"
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

                    line = f"[{i}] {company_name} - {title} | Approved: {approved_at} | Stipend: {stipend} | CTC: {ctc}"
                    print(line.encode("ascii", errors="replace").decode("ascii"))
                    if job_id:
                        print(f"    Link: https://recruit.thapar.edu/job/{job_id}")
                    print("-" * 70)
            else:
                print("Error fetching mappings:", map_resp.text)
        else:
            print("Refresh failed:", resp.text)

if __name__ == "__main__":
    fetch_live_jobs()
