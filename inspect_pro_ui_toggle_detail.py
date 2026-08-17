import re
import httpx

def inspect_nx():
    url = "https://recruit.thapar.edu/assets/index-QXv2-F8P.js"
    print("=== Inspecting Ht and nx helper functions in RecruitSage JS ===")
    
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(url)
        if resp.status_code == 200:
            code = resp.text
            
            # Find definition of Ht and nx
            pos = code.find("FF_STUDENT_PRO_UI")
            snippet = code[max(0, pos-400):min(len(code), pos+400)]
            print("--- Ht / Feature Flag Definition ---")
            print(snippet.encode("ascii", errors="replace").decode("ascii"))
            
            pos_nx = code.find("studentProUi")
            snippet_nx = code[max(0, pos_nx-200):min(len(code), pos_nx+400)]
            print("\n--- Toggle Function Definition ---")
            print(snippet_nx.encode("ascii", errors="replace").decode("ascii"))

if __name__ == "__main__":
    inspect_nx()
