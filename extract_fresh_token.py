import time
import json
from playwright.sync_api import sync_playwright
from state import get_session, Meta
from dotenv import load_dotenv

load_dotenv()

def extract_and_save():
    print("=== Launching Browser Login to Extract Fresh Session Token ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://recruit.thapar.edu/login")
        page.fill("input[type='email']", "mgupta6_be23@thapar.edu")
        page.fill("input[type='password']", "Alpha@123")
        page.click("button[type='submit']")
        
        # Wait up to 10s for navigation or token insertion
        page.wait_for_timeout(5000)
        
        token = page.evaluate("""() => {
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.includes("auth-token")) {
                    try {
                        const val = JSON.parse(localStorage.getItem(key));
                        return val.refresh_token || null;
                    } catch (e) {}
                }
            }
            return null;
        }""")
        
        browser.close()
        
        if token:
            print(f"Extracted Fresh Refresh Token: {token}")
            session = get_session()
            row = session.query(Meta).filter(Meta.key == "refresh_token").first()
            if not row:
                row = Meta(key="refresh_token", value=token)
                session.add(row)
            else:
                row.value = token
            session.commit()
            session.close()
            print("Successfully saved fresh token into PostgreSQL meta table!")
            return token
        else:
            print("Could not extract token automatically (CAPTCHA step required).")
            return None

if __name__ == "__main__":
    extract_and_save()
