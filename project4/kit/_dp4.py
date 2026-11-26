"""Shared constants and the event generator for the Project 4 kit. Do not edit."""
import json
import random
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path

import _aws

PROJECT = Path(__file__).resolve().parent.parent      # .../project4
APP_DIR = PROJECT / "access-events"
OUT = PROJECT / "out"                                   # local copies of every uploaded file (git-ignored)
BUCKET = "ds3022-access-events"
STACK = "ds3022-dp4"
QUEUE, DLQ = "access-file-events", "access-file-dlq"

BUILDINGS = ["A01", "B02", "C03", "D04", "E05", "F06", "G07", "H08", "I09", "J10"]
CHECK_DATE = "2026-11-02"   # reserved for kit/check_project.py: doors.py never writes events on this date


def users(n=40, seed=3022):
    """A fixed pool of computing IDs in the UVA format (2-3 letters, 1 digit, 1-3 letters)."""
    rng = random.Random(seed)
    pool = set()
    while len(pool) < n:
        pool.add("".join(rng.choices(string.ascii_lowercase, k=rng.choice([2, 3])))
                 + str(rng.randint(0, 9))
                 + "".join(rng.choices(string.ascii_lowercase, k=rng.choice([1, 2, 3]))))
    return sorted(u for u in pool if not u.startswith("chk"))


USERS = users()


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def event(reader, when, user, result="granted", rng=random):
    building, door = reader.split("-")
    return {
        "event_id": f"{reader}-{when.astimezone(timezone.utc):%Y%m%d%H%M%S}-{rng.randrange(16**4):04x}",
        "building_code": building,
        "building_door_id": door,
        "user_identity": user,
        "access_time": iso(when),
        "result": result,
    }


def random_reader(rng=random):
    return f"{rng.choice(BUILDINGS)}-{rng.randint(10, 69)}"


def document(reader, events):
    return {"reader": reader, "uploaded_at": iso(datetime.now(timezone.utc)), "events": events}


def local_copy(key):
    return OUT / key.replace("/", "__")


def upload(key, body, s3=None):
    """Upload text to the bucket and keep a local copy in out/ (for 'again' and 'retry')."""
    OUT.mkdir(exist_ok=True)
    local_copy(key).write_text(body, encoding="utf-8")
    (s3 or _aws.client("s3")).put_object(Bucket=BUCKET, Key=key, Body=body.encode("utf-8"),
                                          ContentType="application/json")


def new_key(reader, suffix=".json", rng=random):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"uploads/{reader}/{stamp}-{rng.randrange(16**4):04x}{suffix}"


def after_hours(access_time_utc):
    """22:00 to 06:00 UTC. access_time_utc like 2026-11-16T23:10:00Z."""
    hour = int(access_time_utc[11:13])
    return hour >= 22 or hour < 6


def dumps(doc):
    return json.dumps(doc, indent=2)


def day_times(date, n, rng):
    """n access times on one UTC date, busy at 08-10, 13-14 and 17-18, about 6% after hours."""
    start = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    weights = [1, 1, 1, 1, 1, 2, 6, 14, 18, 12, 8, 7, 9, 11, 8, 7, 8, 12, 10, 5, 3, 2, 1, 1]
    hours = rng.choices(range(24), weights=weights, k=n)
    return sorted(start + timedelta(hours=h, minutes=rng.randint(0, 59), seconds=rng.randint(0, 59)) for h in hours)
