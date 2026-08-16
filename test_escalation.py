from datetime import datetime, timedelta, timezone
from escalation import evaluate_next_checkpoint

def test_escalation():
    now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    
    # Job deadline in 3 hours -> No checkpoint due yet
    deadline = now + timedelta(hours=3)
    assert evaluate_next_checkpoint(now, deadline, []) is None
    
    # Job deadline in 1h 20m -> 2h and 1.5h due
    deadline_1h20m = now + timedelta(hours=1, minutes=20)
    assert evaluate_next_checkpoint(now, deadline_1h20m, []) == "2h"
    assert evaluate_next_checkpoint(now, deadline_1h20m, ["2h"]) == "1.5h"
    assert evaluate_next_checkpoint(now, deadline_1h20m, ["2h", "1.5h"]) is None

    
    # Job deadline in 45m -> 1h due (or 2h, 1.5h, 1h in order if none sent)
    deadline_45m = now + timedelta(minutes=45)
    assert evaluate_next_checkpoint(now, deadline_45m, []) == "2h"
    assert evaluate_next_checkpoint(now, deadline_45m, ["2h"]) == "1.5h"
    assert evaluate_next_checkpoint(now, deadline_45m, ["2h", "1.5h"]) == "1h"
    assert evaluate_next_checkpoint(now, deadline_45m, ["2h", "1.5h", "1h"]) is None
    
    # Job deadline in 20m -> 30m checkpoint due
    deadline_20m = now + timedelta(minutes=20)
    assert evaluate_next_checkpoint(now, deadline_20m, ["2h", "1.5h", "1h"]) == "30m"
    assert evaluate_next_checkpoint(now, deadline_20m, ["2h", "1.5h", "1h", "30m"]) is None
    
    # Past deadline -> None
    past_deadline = now - timedelta(minutes=5)
    assert evaluate_next_checkpoint(now, past_deadline, []) is None

    print("ALL unit tests in test_escalation.py PASSED!")

if __name__ == "__main__":
    test_escalation()
