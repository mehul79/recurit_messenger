from state import get_session, Meta

def set_token():
    session = get_session()
    row = session.query(Meta).filter(Meta.key == "refresh_token").first()
    token_val = "sbl23k4yzrev"
    if not row:
        row = Meta(key="refresh_token", value=token_val)
        session.add(row)
    else:
        row.value = token_val
    session.commit()
    print(f"PostgreSQL meta table refresh_token updated to: {token_val}")
    session.close()

if __name__ == "__main__":
    set_token()
