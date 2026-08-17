import re
import httpx

def find_routes_in_bundle():
    print("=== Scanning RecruitSage Frontend JavaScript Bundle for Routes ===")
    
    with httpx.Client(timeout=15.0) as client:
        resp = client.get("https://recruit.thapar.edu")
        html = resp.text
        print(f"Index HTML length: {len(html)} bytes")
        
        # Find script tags
        js_files = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html)
        print(f"Found {len(js_files)} JS files in index HTML:")
        for js in js_files:
            print(f"  - {js}")

            js_url = js if js.startswith("http") else f"https://recruit.thapar.edu{js}"
            try:
                js_resp = client.get(js_url)
                if js_resp.status_code == 200:
                    code = js_resp.text
                    # Search for route paths in JS code
                    paths = set(re.findall(r'["\'](/[^"\'\s>]+)["\']', code))
                    job_paths = [p for p in paths if any(k in p for k in ["job", "dashboard", "event", "application"])]
                    print(f"    Found {len(job_paths)} relevant route patterns:")
                    for jp in sorted(job_paths)[:15]:
                        print(f"      -> {jp}")
            except Exception as e:
                print(f"    Failed to fetch {js_url}: {e}")

if __name__ == "__main__":
    find_routes_in_bundle()
