from state import init_db, get_session, Job, JobState, NotificationLog, Meta
from datetime import datetime, timezone

def test_connection():
    print("=== Testing Database Connection & Initializing Schema ===")
    try:
        init_db()
        print("Schema tables created / verified successfully!")
        
        session = get_session()
        # Test basic query
        count = session.query(Job).count()
        print(f"Current Jobs in DB: {count}")
        session.close()
        print("Database connection test PASSED!")
        return True
    except Exception as e:
        print("Database connection error:", e)
        return False

if __name__ == "__main__":
    test_connection()
