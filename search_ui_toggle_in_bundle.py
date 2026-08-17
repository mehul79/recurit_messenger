import re
import httpx

def search_ui_toggle():
    url = "https://recruit.thapar.edu/assets/index-QXv2-F8P.js"
    print("=== Searching for UI Switch / Toggle Flags in RecruitSage JS Bundle ===")
    
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(url)
        if resp.status_code == 200:
            code = resp.text
            
            # Keywords to search
            keywords = ["ui", "classic", "legacy", "v2", "beta", "new_ui", "toggle", "version", "theme", "view"]
            
            found = set()
            for kw in keywords:
                matches = re.findall(rf'["\']([^"\'\s>]{{2,30}}{kw}[^"\'\s>]{{0,30}})["\']', code, re.IGNORECASE)
                for m in matches:
                    if any(x in m.lower() for x in ["classic", "new", "v2", "beta", "ui", "toggle"]):
                        found.add(m)

            print(f"Found {len(found)} candidate UI toggles/flags:")
            for item in sorted(found)[:30]:
                print(f"  - {item}")
        else:
            print("Failed to download JS bundle:", resp.status_code)

if __name__ == "__main__":
    search_ui_toggle()
