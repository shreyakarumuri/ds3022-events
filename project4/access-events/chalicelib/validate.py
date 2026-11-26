"""Data-quality rules R1 to R6 for one access event (BRIEF.md, "The rules").

check() returns (normalised_event, None) for a valid event, or (None, reason) for a
rejected one. Start every reason with the rule number ("R4 bad user_identity"): your
tests and your file_log use it.
"""
import re
from datetime import datetime, timedelta, timezone  # noqa: F401  (you will need them)

FIELDS = ["event_id", "building_code", "building_door_id", "user_identity", "access_time", "result"]
BUILDINGS = {"A01", "B02", "C03", "D04", "E05", "F06", "G07", "H08", "I09", "J10"}
USER_ID = re.compile(r"^[a-z]{2,3}[0-9][a-z]{1,3}$")
MAX_FUTURE = timedelta(minutes=5)


def check(event, now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(event, dict):
        return None, "R1 not an object"
    for f in FIELDS:                                                        # R1 (given)
        if event.get(f) in (None, ""):
            return None, f"R1 missing {f}"
    # TODO C1: R2 building_code is one of BUILDINGS
    # TODO C2: R3 building_door_id is a whole number from 10 to 69 (it arrives as text, e.g. "23")
    # TODO C3: R4 user_identity matches USER_ID
    # TODO C4: R5 access_time is ISO 8601 WITH a time zone, and not more than MAX_FUTURE after now
    # TODO C5: R6 result is "granted" or "denied"
    # TODO C6: return a normalised copy: the six fields only, as text, access_time converted to UTC
    #          in the form YYYY-MM-DDTHH:MM:SSZ (2026-11-16T00:30:00+01:00 -> 2026-11-15T23:30:00Z)
    raise NotImplementedError("check")


def split(document, now=None):
    """Given: {"reader", "uploaded_at", "events": [...]} -> (valid, rejected [{index, reason}])."""
    if not isinstance(document, dict) or not isinstance(document.get("events"), list):
        return [], [{"index": None, "reason": "no 'events' list"}]
    valid, rejected = [], []
    for i, e in enumerate(document["events"]):
        clean, reason = check(e, now)
        if reason:
            rejected.append({"index": i, "reason": reason})
        else:
            valid.append(clean)
    return valid, rejected
