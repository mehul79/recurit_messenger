import re
import httpx

def find_pro_ui_logic():
    url = "https://recruit.thapar.edu/assets/index-QXv2-F8P.js"
    print("=== Inspecting FF_STUDENT_PRO_UI in RecruitSage JS Bundle ===")
    
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(url)
        if resp.status_code == 200:
            code = resp.text
            
            # Find snippets containing FF_STUDENT_PRO_UI or studentProUi
            matches = [m.start() for m in re.finditer(r'FF_STUDENT_PRO_UI|studentProUi', code)]
            print(f"Found {len(matches)} occurrences of Pro UI flags:")
            for idx, pos in enumerate(matches, 1):
                start = max(0, pos - 200)
                end = min(len(code), pos + 200)
                snippet = code[start:end]
                print(f"\n--- Snippet #{idx} ---")
                print(snippet)
        else:
            print("Failed to download JS bundle:", resp.status_code)

if __name__ == "__main__":
    find_pro_ui_logic()
