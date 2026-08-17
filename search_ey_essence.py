import httpx
from state import get_session, Meta
from portal import get_supabase_url, get_supabase_anon, update_stored_tokens

def search_company():
    session = get_session()
    meta_row = session.query(Meta).filter(Meta.key == "refresh_token").first()
    db_refresh_token = meta_row.value if meta_row else None
    session.close()

    url_base = get_supabase_url()
    anon_key = get_supabase_anon()

    # Get fresh access token
    url = f"{url_base}/auth/v1/token?grant_type=refresh_token"
    headers = {
        "apikey": anon_key,
        "Content-Type": "application/json"
    }
    payload = {"refresh_token": db_refresh_token}

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            print("Refresh token error:", resp.status_code, resp.text)
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

        print("=== Searching for EY / Essence / Recent Postings ===")
        
        # 1. Search in companies table
        comp_url = f"{url_base}/rest/v1/companies?select=*&limit=500"
        resp_c = client.get(comp_url, headers=headers_auth)
        if resp_c.status_code == 200:
            companies = resp_c.json()
            print(f"Total companies in database: {len(companies)}")
            for c in companies:
                name = c.get("name", "")
                if any(kw in name.lower() for kw in ["ey", "ernst", "essence", "health", "essentia"]):
                    print(f" -> Found matching company: {name} (ID: {c.get('id')})")

        # 2. Query ALL jobs_posted ordered by created_at.desc (limit 100)
        jobs_url = f"{url_base}/rest/v1/jobs_posted?select=*,companies(*)&order=created_at.desc&limit=100"
        resp_j = client.get(jobs_url, headers=headers_auth)
        if resp_j.status_code == 200:
            jobs = resp_j.json()
            print(f"\nTotal jobs in jobs_posted: {len(jobs)}")
            for i, j in enumerate(jobs, 1):
                company_info = j.get("companies") or {}
                company_name = company_info.get("name") if isinstance(company_info, dict) else "Company"
                title = j.get("title") or "Role"
                created_at = j.get("created_at") or "N/A"
                if any(kw in (company_name + title).lower() for kw in ["ey", "ernst", "essence", "health", "essentia"]):
                    print(f" *** MATCH *** [{i}] {company_name} - {title} | Posted: {created_at} | ID: {j.get('id')}")

if __name__ == "__main__":
    search_company()
