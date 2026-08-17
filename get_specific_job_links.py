import httpx
from portal import get_valid_access_token, get_supabase_url, get_supabase_anon

def get_links():
    token = get_valid_access_token()
    headers = {
        "apikey": get_supabase_anon(),
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url_base = get_supabase_url()
    
    map_url = f"{url_base}/rest/v1/job_university_mappings?select=*,jobs_posted(*,companies(*))&status=eq.Approved&order=approved_at.desc.nullslast&limit=30"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(map_url, headers=headers)
        if resp.status_code == 200:
            mappings = resp.json()
            targets = ["akamai", "zepto", "axis", "istec"]
            print("\n" + "="*70)
            print("DIRECT PORTAL LINKS FOR AKAMAI, ZEPTO, AXIS BANK, ISTEC:")
            print("="*70)

            for m in mappings:
                jp = m.get("jobs_posted") or {}
                company_info = jp.get("companies") or {}
                company_name = company_info.get("name") if isinstance(company_info, dict) else "Company"
                title = jp.get("title") or "Role"
                job_id = jp.get("id")

                if any(t in company_name.lower() for t in targets):
                    print(f"Company: {company_name}")
                    print(f"Title:   {title}")
                    print(f"Job ID:  {job_id}")
                    print(f"Link:    https://recruit.thapar.edu/job/{job_id}")
                    print("-" * 70)

if __name__ == "__main__":
    get_links()
