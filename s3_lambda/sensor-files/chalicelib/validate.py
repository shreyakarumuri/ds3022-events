"""Data-quality rules for one sensor file. Pure functions: easy to test without AWS."""
import re
from datetime import datetime
from decimal import Decimal

DEVICE_ID = re.compile(r"^sensor-\d{3}$")


def check(reading):
    """Return None if the reading is valid, otherwise a short reason."""
    if not isinstance(reading, dict):
        return "not an object"
    for field in ("device_id", "timestamp", "temperature"):
        if reading.get(field) is None:
            return f"missing {field}"
    if not isinstance(reading["device_id"], str) or not DEVICE_ID.match(reading["device_id"]):
        return "bad device_id"
    try:
        ts = datetime.fromisoformat(str(reading["timestamp"]).replace("Z", "+00:00"))
    except ValueError:
        return "timestamp is not ISO 8601"
    if ts.tzinfo is None:
        return "timestamp has no time zone"
    t = reading["temperature"]
    if isinstance(t, bool) or not isinstance(t, (int, Decimal)):
        return "temperature is not a number"
    if not -40 <= t <= 150:
        return "temperature out of range (-40 to 150 F)"
    h = reading.get("humidity")
    if h is not None and (isinstance(h, bool) or not isinstance(h, (int, Decimal)) or not 0 <= h <= 100):
        return "humidity out of range (0 to 100)"
    return None


def split(document):
    """document = {"metadata": {...}, "readings": [...]} -> (valid readings, rejected [{index, reason}])."""
    if not isinstance(document, dict) or not isinstance(document.get("readings"), list):
        return [], [{"index": None, "reason": "no 'readings' list"}]
    valid, rejected = [], []
    for i, r in enumerate(document["readings"]):
        reason = check(r)
        if reason:
            rejected.append({"index": i, "reason": reason})
        else:
            valid.append(r)
    return valid, rejected
