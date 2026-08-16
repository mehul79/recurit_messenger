import json
import httpx
from portal import get_valid_access_token, SUPABASE_URL, SUPABASE_ANON

def inspect_schema():
    token = get_valid_access_token()
    headers = {
        "apikey": SUPABASE_ANON,
        "Authorization": f"Bearer {token}"
    }
    
    print("=== Inspecting Supabase OpenAPI Schema ===")
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(f"{SUPABASE_URL}/rest/v1/", headers=headers)
        print(f"OpenAPI Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            paths = data.get("paths", {})
            print(f"Total Endpoints Found: {len(paths)}")
            
            rpc_funcs = []
            tables = []
            
            for path in paths:
                if path.startswith("/rpc/"):
                    rpc_funcs.append(path.replace("/rpc/", ""))
                elif path.startswith("/"):
                    tables.append(path.replace("/", ""))
                    
            print("\nAvailable RPC Functions:")
            for f in sorted(rpc_funcs):
                print(f" - {f}")
                
            print("\nAvailable Tables / Views:")
            for t in sorted(tables):
                print(f" - {t}")
        else:
            print("Failed to get OpenAPI spec:", resp.text)

if __name__ == "__main__":
    inspect_schema()
