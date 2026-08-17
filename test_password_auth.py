import os
import httpx
from portal import get_supabase_url, get_supabase_anon, login_with_password

def test_auth():
    print("=== Testing Direct Email/Password Auth ===")
    try:
        access_token = login_with_password()
        print("SUCCESS! Access token generated:", access_token[:30])
    except Exception as e:
        print("Auth Exception:", e)

if __name__ == "__main__":
    test_auth()
