import os
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://api.recruit.thapar.edu")
SUPABASE_ANON = os.getenv("SUPABASE_ANON")

def test_refresh(refresh_token: str):
    print("=== Testing Supabase Token Refresh ===")
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token"
    headers = {
        "apikey": SUPABASE_ANON,
        "Content-Type": "application/json"
    }
    payload = {
        "refresh_token": refresh_token
    }
    
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        print(f"Response Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            new_access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token")
            print("SUCCESS! Token refresh works without Turnstile CAPTCHA!")
            print(f"New Access Token: {new_access_token[:25]}...")
            print(f"New Refresh Token: {new_refresh_token[:25]}...")
            return True, data
        else:
            print("FAILED token refresh!")
            print(f"Response Body: {resp.text}")
            return False, resp.text

if __name__ == "__main__":
    import sys
    token = os.getenv("PORTAL_REFRESH_TOKEN")
    if not token and len(sys.argv) > 1:
        token = sys.argv[1]
    
    if not token:
        print("Please set PORTAL_REFRESH_TOKEN in .env or pass it as an argument: python test_refresh_token.py <refresh_token>")
    else:
        test_refresh(token)
