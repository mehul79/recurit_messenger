import os
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://api.recruit.thapar.edu")
SUPABASE_ANON = os.getenv("SUPABASE_ANON")
PORTAL_EMAIL = os.getenv("PORTAL_EMAIL")
PORTAL_PASSWORD = os.getenv("PORTAL_PASSWORD")

def test_supabase_login():
    print("=== Step 0: Testing Headless Supabase Login ===")
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Target Email: {PORTAL_EMAIL}")
    
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": SUPABASE_ANON,
        "Content-Type": "application/json"
    }
    payload = {
        "email": PORTAL_EMAIL,
        "password": PORTAL_PASSWORD
    }
    
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        print(f"Response Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            access_token = data.get("access_token", "")
            refresh_token = data.get("refresh_token", "")
            user_id = data.get("user", {}).get("id", "")
            print("SUCCESS! Headless password login works.")
            print(f"User ID: {user_id}")
            print(f"Access Token (prefix): {access_token[:25]}...")
            print(f"Refresh Token (prefix): {refresh_token[:25]}...")
            return True, data
        else:
            print("FAILED or Turnstile Enforced!")
            print(f"Response Body: {resp.text}")
            return False, resp.text

if __name__ == "__main__":
    test_supabase_login()
