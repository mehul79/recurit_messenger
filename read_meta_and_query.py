from state import get_session, Meta
import httpx
from portal import get_supabase_url, get_supabase_anon

def query():
    session = get_session()
    meta = session.query(Meta).filter(Meta.key == "refresh_token").first()
    val = meta.value if meta else "None"
    session.close()
    print(f"Meta refresh_token length: {len(val)} | sample: {val[:20]}")

    url_base = get_supabase_url()
    anon_key = get_supabase_anon()

    url = f"{url_base}/auth/v1/token?grant_type=refresh_token"
    headers = {"apikey": anon_key, "Content-Type": "application/json"}

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, headers=headers, json={"refresh_token": val})
        print("Refresh status:", resp.status_code)
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            auth_headers = {"apikey": anon_key, "Authorization": f"Bearer {token}"}
            
            # Inspect Zepto job eligibilities
            j_resp = client.get(f"{url_base}/rest/v1/job_eligibilities?select=*&job_id=eq.e1942047-8e82-4b62-8bb4-e5a6d24f812a", headers=auth_headers)
            print("\nZEPTO ELIGIBILITIES ROW:")
            print(j_resp.json())

            # Inspect Akamai job eligibilities
            a_resp = client.get(f"{url_base}/rest/v1/job_eligibilities?select=*&job_id=eq.97c85300-e9c2-413a-bd5e-18883761b04e", headers=auth_headers)
            print("\nAKAMAI ELIGIBILITIES ROW:")
            print(a_resp.json())

if __name__ == "__main__":
    query()
