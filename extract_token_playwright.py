import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

PORTAL_EMAIL = os.getenv("PORTAL_EMAIL", "mgupta6_be23@thapar.edu")
PORTAL_PASSWORD = os.getenv("PORTAL_PASSWORD", "Alpha@123")

def run():
    from playwright.sync_api import sync_playwright

    print("=== Launching Playwright (Interactive Headed Window) ===", flush=True)
    with sync_playwright() as p:
        # Launch Chromium headed with max viewport
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
        )
        context = browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("Navigating to https://recruit.thapar.edu ...", flush=True)
        page.goto("https://recruit.thapar.edu", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        email_el = page.query_selector("input[type='email'], input[name='email'], input[placeholder*='email' i], input[id='email']")
        pass_el = page.query_selector("input[type='password'], input[name='password'], input[placeholder*='password' i], input[id='password']")

        if email_el and pass_el:
            print("Auto-filling email and password...", flush=True)
            email_el.fill(PORTAL_EMAIL)
            pass_el.fill(PORTAL_PASSWORD)

        print("\n>>> PLEASE CLICK 'LOGIN' (AND CHECK THE TURNSTILE CAPTCHA BOX IF PROMPTED) IN THE BROWSER WINDOW <<<\n", flush=True)

        refresh_token = None
        for i in range(60): # 120 seconds total
            time.sleep(2)
            try:
                storage_data = page.evaluate("() => JSON.stringify(localStorage)")
                if storage_data:
                    storage_dict = json.loads(storage_data)

                    for key, val in storage_dict.items():
                        # Search for refresh token in any JSON string or raw value
                        if "refresh_token" in str(val) or "access_token" in str(val):
                            try:
                                token_obj = json.loads(val)
                                if isinstance(token_obj, dict):
                                    if "refresh_token" in token_obj:
                                        refresh_token = token_obj["refresh_token"]
                                    elif "currentSession" in token_obj and "refresh_token" in token_obj["currentSession"]:
                                        refresh_token = token_obj["currentSession"]["refresh_token"]
                            except Exception:
                                pass

                            if not refresh_token and "refresh_token" in str(val):
                                # Try regex extraction if JSON parsing didn't match standard schema
                                import re
                                match = re.search(r'"refresh_token"\s*:\s*"([^"]+)"', str(val))
                                if match:
                                    refresh_token = match.group(1)

                        if refresh_token:
                            print(f"\nSUCCESS! Found refresh_token in localStorage key '{key}'!", flush=True)
                            break
            except Exception as e:
                pass

            if refresh_token:
                break

            if i % 5 == 0:
                print(f"Waiting for login... ({i*2}s/120s) Current URL: {page.url}", flush=True)

        browser.close()

        if refresh_token:
            print(f"Extracted Refresh Token: {refresh_token[:30]}...", flush=True)

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
            print("Successfully updated .env with PORTAL_REFRESH_TOKEN!", flush=True)
            return refresh_token
        else:
            print("Timed out waiting for login.", flush=True)
            return None

if __name__ == "__main__":
    run()
