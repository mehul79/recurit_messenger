import time
from playwright.sync_api import sync_playwright
import httpx
from portal import get_valid_access_token, get_supabase_url, get_supabase_anon

def inspect_routes():
    print("=== Inspecting RecruitSage Frontend Job URLs ===")
    
    # 1. Fetch live access token
    token = get_valid_access_token()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Set localStorage Supabase session
        page.goto("https://recruit.thapar.edu/login")
        
        # Inject auth token into localStorage
        session_data = {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 3600,
            "refresh_token": "sbl23k4yzrev",
            "user": {"email": "mgupta6_be23@thapar.edu"}
        }
        
        page.evaluate(f"""() => {{
            const key = Object.keys(localStorage).find(k => k.includes('auth-token')) || 'sb-kqoqgzhjmmvvhgevyfph-auth-token';
            localStorage.setItem(key, JSON.stringify({session_data}));
        }}""")

        # Navigate to dashboard
        page.goto("https://recruit.thapar.edu/dashboard")
        page.wait_for_timeout(3000)
        
        print(f"Dashboard URL: {page.url}")
        
        # Find job links / cards on the dashboard
        links = page.query_selector_all("a[href*='job']")
        print(f"Found {len(links)} links matching 'job':")
        for idx, link in enumerate(links[:10], 1):
            href = link.get_attribute("href")
            text = link.inner_text()
            print(f" [{idx}] href: {href} | Text: {text.strip()[:30]}")

        browser.close()

if __name__ == "__main__":
    inspect_routes()
