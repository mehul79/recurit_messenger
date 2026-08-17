"""Checks the token chain can't silently lose a rotated refresh token.

Runs against the real DATABASE_URL (needs Postgres for pg_advisory_xact_lock) but
snapshots and restores the live meta rows, so it never leaves a bogus token behind.
No network: the refresh grant is stubbed.
"""
import time
import portal
from state import get_session, Meta

KEYS = ("refresh_token", "access_token", "access_expires_at", "auth_alert_sent")


def snapshot():
    s = get_session()
    try:
        return {m.key: m.value for m in s.query(Meta).filter(Meta.key.in_(KEYS)).all()}
    finally:
        s.close()


def restore(snap):
    s = get_session()
    try:
        for m in s.query(Meta).filter(Meta.key.in_(KEYS)).all():
            if m.key in snap:
                m.value = snap[m.key]
            else:
                s.delete(m)
        s.commit()
    finally:
        s.close()


def set_refresh(value):
    s = get_session()
    try:
        row = s.query(Meta).filter(Meta.key == "refresh_token").first()
        if row:
            row.value = value
        else:
            s.add(Meta(key="refresh_token", value=value))
        for key in ("access_token", "access_expires_at"):
            r = s.query(Meta).filter(Meta.key == key).first()
            if r:
                r.value = ""
        s.commit()
    finally:
        s.close()


def read(key):
    s = get_session()
    try:
        row = s.query(Meta).filter(Meta.key == key).first()
        return row.value if row else None
    finally:
        s.close()


def demo():
    snap = snapshot()
    real_grant = portal._refresh_grant
    calls = []
    try:
        # 1. rotation is persisted before the access token is handed out
        portal._refresh_grant = lambda rt: (
            calls.append(rt),
            {"access_token": "AT1", "refresh_token": "ROTATED1", "expires_in": 3600},
        )[1]
        portal._token_cache.update(access_token=None, expires_at=0)
        set_refresh("SEED0")
        assert portal.get_valid_access_token() == "AT1"
        assert calls == ["SEED0"], calls
        assert read("refresh_token") == "ROTATED1", read("refresh_token")

        # 2. a warm cache does not burn another rotation
        assert portal.get_valid_access_token() == "AT1"
        assert len(calls) == 1, calls

        # 3. cold process reuses the DB-cached access token instead of refreshing
        portal._token_cache.update(access_token=None, expires_at=0)
        assert portal.get_valid_access_token() == "AT1"
        assert len(calls) == 1, calls

        # 4. a rejected refresh raises AuthDead and never clobbers the stored token
        def dead(rt):
            raise portal.AuthDead("HTTP 400 invalid refresh token")

        portal._refresh_grant = dead
        portal._token_cache.update(access_token=None, expires_at=0)
        set_refresh("ROTATED1")
        try:
            portal.get_valid_access_token()
            raise AssertionError("expected AuthDead")
        except portal.AuthDead:
            pass
        assert read("refresh_token") == "ROTATED1", read("refresh_token")

        # 5. an expired DB-cached access token is not reused
        s = get_session()
        try:
            s.query(Meta).filter(Meta.key == "access_expires_at").first().value = str(time.time() - 1)
            s.commit()
        finally:
            s.close()
        try:
            portal.get_valid_access_token()
            raise AssertionError("expected AuthDead on expired cache")
        except portal.AuthDead:
            pass

        print("auth chain OK")
    finally:
        portal._refresh_grant = real_grant
        portal._token_cache.update(access_token=None, expires_at=0)
        restore(snap)


if __name__ == "__main__":
    demo()
