import os
import json
import time
import sys
from dotenv import load_dotenv

load_dotenv()

PORTAL_EMAIL = os.getenv("PORTAL_EMAIL", "mgupta6_be23@thapar.edu")
PORTAL_PASSWORD = os.getenv("PORTAL_PASSWORD", "Alpha@123")

def launch_login():
    from playwright.sync_api import sync_playwright

    print("=== Opening Chrome Window for RecruitSage Login ===", flush=True)
    with sync_playwright() as p:
        browser = None
        # Try launching real installed Google Chrome first, fallback to Chromium
        try:
            browser = p.chromium.launch(
                channel="chrome",
                headless=False,
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
            )
            print("Launched system Google Chrome.", flush=True)
        except Exception:
            browser = p.chromium.launch(
                headless=False,
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
            )
            print("Launched Playwright Chromium.", flush=True)

        context = browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("Navigating to https://recruit.thapar.edu ...", flush=True)
        page.goto("https://recruit.thapar.edu", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        email_el = page.query_selector("input[type='email'], input[name='email'], input[placeholder*='email' i], input[id='email']")
        pass_el = page.query_selector("input[type='password'], input[name='password'], input[placeholder*='password' i], input[id='password']")

        if email_el and pass_el:
            print("Auto-filling email and password fields...", flush=True)
            email_el.fill(PORTAL_EMAIL)
            pass_el.fill(PORTAL_PASSWORD)

        print("\n" + "="*70, flush=True)
        print("ACTION REQUIRED ON YOUR SCREEN:", flush=True)
        print("1. Look at the open Chrome browser window.")
        print("2. Click the Cloudflare Turnstile CAPTCHA checkbox.")
        print("3. Click the 'Login' button.")
        print("="*70 + "\n", flush=True)

        refresh_token = None
        for i in range(90): # 180 seconds window
            time.sleep(2)
            try:
                storage_data = page.evaluate("() => JSON.stringify(localStorage)")
                if storage_data:
                    storage_dict = json.loads(storage_data)
                    for key, val in storage_dict.items():
                        if "refresh_token" in str(val):
                            import re
                            match = re.search(r'"refresh_token"\s*:\s*"([^"]+)"', str(val))
                            if match:
                                refresh_token = match.group(1)
                                print(f"Detected login! Extracted refresh_token from key '{key}'", flush=True)
                                break
            except Exception:
                pass

            if refresh_token:
                break

            if (i + 1) % 5 == 0:
                print(f"Waiting for login... ({(i+1)*2}s / 180s) URL: {page.url}", flush=True)

        browser.close()

        if refresh_token:
            print("\nUpdating .env and DB meta table with PORTAL_REFRESH_TOKEN...", flush=True)
            # Update .env
            env_path = ".env"
            env_content = ""
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    env_content = f.read()

            if "PORTAL_REFRESH_TOKEN=" in env_content:
                lines = env_content.splitlines()
                new_lines = []
                for line in lines:
                    if line.startswith("PORTAL_REFRESH_TOKEN="):
                        new_lines.append(f"PORTAL_REFRESH_TOKEN={refresh_token}")
                    else:
                        new_lines.append(line)
                env_content = "\n".join(new_lines)
            else:
                env_content += f"\nPORTAL_REFRESH_TOKEN={refresh_token}\n"

            with open(env_path, "w", encoding="utf-8") as f:
                f.write(env_content)

            # Update DB meta table
            from portal import update_stored_tokens
            update_stored_tokens("temp_access_token", refresh_token)

            print("SUCCESS: Token saved to .env & Database!", flush=True)

            print("\n=== Testing Direct Supabase RPC API Call with New Token ===", flush=True)
            from portal import fetch_eligible_jobs
            jobs = fetch_eligible_jobs()
            print(f"Fetched {len(jobs)} eligible job(s) directly from get_eligible_jobs_rpc!", flush=True)
            for j in jobs[:3]:
                title = j.get("job_title") or j.get("title")
                company = j.get("company_name") or j.get("company")
                print(f" - {company} · {title} (ID: {j.get('id') or j.get('job_id')})")

            return True
        else:
            print("\nTimed out waiting for browser login.", flush=True)
            return False

if __name__ == "__main__":
    launch_login()
