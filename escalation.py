from datetime import datetime, timedelta, timezone

CHECKPOINTS = [
    ("2h", timedelta(hours=2)),
    ("1.5h", timedelta(hours=1, minutes=30)),
    ("1h", timedelta(hours=1)),
    ("30m", timedelta(minutes=30)),
]

def evaluate_next_checkpoint(now: datetime, deadline: datetime, checkpoints_sent: list or set) -> str or None:
    """
    Evaluates which deadline checkpoint (if any) is due to fire based on current time.
    Checkpoints fire in order (2h -> 1.5h -> 1h -> 30m).
    
    Rules:
    - If deadline has already passed (now >= deadline), return None.
    - Checkpoints already in `checkpoints_sent` are skipped.
    - A checkpoint fires when `now >= deadline - delta`.
    - Returns the first un-sent checkpoint label that is due, or None.
    """
    if not deadline or not now:
        return None
        
    # Ensure timezone awareness
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
        
    if now >= deadline:
        return None

    time_remaining = deadline - now

    for label, delta in CHECKPOINTS:
        if label in checkpoints_sent:
            continue
        # If we have reached or passed this checkpoint window (time_remaining <= delta)
        if time_remaining <= delta:
            return label
            
    return None
