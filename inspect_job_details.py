import httpx
from portal import get_valid_access_token, SUPABASE_URL, SUPABASE_ANON

def inspect_details():
    token = get_valid_access_token()
    headers = {
        "apikey": SUPABASE_ANON,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("=== Querying job_eligibilities ===")
    url = f"{SUPABASE_URL}/rest/v1/job_eligibilities?select=*&limit=5"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            print(f"Count: {len(data)}")
            if data:
                print("Sample job_eligibility fields:", list(data[0].keys()))
                print("Sample row:", data[0])

    print("\n=== Querying job_salaries ===")
    url_sal = f"{SUPABASE_URL}/rest/v1/job_salaries?select=*&limit=5"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url_sal, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            print(f"Count: {len(data)}")
            if data:
                print("Sample job_salaries fields:", list(data[0].keys()))
                print("Sample row:", data[0])

    print("\n=== Querying job_university_mappings ===")
    url_uni = f"{SUPABASE_URL}/rest/v1/job_university_mappings?select=*&limit=5"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url_uni, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            print(f"Count: {len(data)}")
            if data:
                print("Sample job_university_mappings fields:", list(data[0].keys()))
                print("Sample row:", data[0])

if __name__ == "__main__":
    inspect_details()
