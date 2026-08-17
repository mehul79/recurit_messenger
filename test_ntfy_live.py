import httpx
from notify import send_new_job_push, NTFY_TOPIC

def test_ntfy():
    print(f"=== Sending Live Test Notification to ntfy Topic: {NTFY_TOPIC} ===")
    
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    headers = {
        "Title": "System Health Check: Thapar Job Watcher Active",
        "Priority": "default",
        "Tags": "white_check_mark,robot",
        "Click": "https://recruit.thapar.edu/student/jobs"
    }
    body = "Testing ntfy notification system delivery.\nFastCron heartbeat and Render watcher service are running smoothly!"

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, data=body.encode("utf-8"), headers=headers)
        print(f"ntfy.sh HTTP Response Status: {resp.status_code}")
        print(f"ntfy.sh Response Body: {resp.text}")
        if resp.status_code == 200:
            print("\nTEST NOTIFICATION DISPATCHED SUCCESSFULLY! Check your phone / ntfy app now!")
        else:
            print("\nFailed to send ntfy notification.")

if __name__ == "__main__":
    test_ntfy()
