import urllib.request
import re

url = "https://recruit.thapar.edu/assets/index-BRCzcXiJ.js"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

print("=== Searching Frontend JS for Supabase Tables & RPCs ===")
with urllib.request.urlopen(req) as resp:
    js_content = resp.read().decode('utf-8')
    print("JS bundle size:", len(js_content))

    # Find .from("...") calls
    from_matches = set(re.findall(r'\.from\s*\(\s*["\']([^"\']+)["\']\s*\)', js_content))
    print("\nSupabase Tables (.from):")
    for tbl in sorted(from_matches):
        print(f" - {tbl}")

    # Find .rpc("...") calls
    rpc_matches = set(re.findall(r'\.rpc\s*\(\s*["\']([^"\']+)["\']\s*\)', js_content))
    print("\nSupabase RPCs (.rpc):")
    for rpc in sorted(rpc_matches):
        print(f" - {rpc}")
