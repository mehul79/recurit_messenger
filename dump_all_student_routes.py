import re
import httpx

def dump_student_routes():
    url = "https://recruit.thapar.edu/assets/index-QXv2-F8P.js"
    print("=== DUMPING STUDENT ROUTES FROM JS BUNDLE ===")
    
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(url)
        if resp.status_code == 200:
            code = resp.text
            # Find all string literals starting with /
            all_routes = set(re.findall(r'["\'](/[^"\'\s><}{]+)["\']', code))
            
            print("--- ALL STUDENT ROUTE PATTERNS ---")
            student_routes = [r for r in all_routes if "student" in r or "job" in r or "event" in r or "dashboard" in r]
            for r in sorted(student_routes):
                print(f"  {r}")
        else:
            print("Error fetching JS bundle:", resp.status_code)

if __name__ == "__main__":
    dump_student_routes()
