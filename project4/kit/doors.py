"""Project 4: badge readers that drop event files into your bucket. Do not edit.

Each file is one upload from one door reader:
    {"reader": "A01-23", "uploaded_at": "...Z", "events": [ {event_id, building_code,
     building_door_id, user_identity, access_time, result}, ... ]}

Run from the project4 folder:
    python kit/doors.py normal                  # 5 files of recent events (last hour)
    python kit/doors.py normal --files 20 --seed 7
    python kit/doors.py day 2026-12-01          # a whole day: 40 files, busy mornings, a few after-hours entries
    python kit/doors.py again <key>             # card C1: upload the same file again (same key)
    python kit/doors.py retry <key>             # card C2: the reader retries: same events, new file name
    python kit/doors.py bad                     # card C3: 10 good events + 6 bad ones (one per rule)
    python kit/doors.py broken                  # card C3: a file that is not JSON
    python kit/doors.py burst --files 200       # card C5: 200 files as fast as possible
    python kit/doors.py late --hours 30         # card C6: events from 30 hours ago arrive now
"""
import argparse
import json
import random
import sys
import time
from datetime import datetime, timedelta, timezone

import _dp4


def summary(key, events, bad=0):
    ah = sum(1 for e in events if e.get("result") == "granted" and isinstance(e.get("access_time"), str)
             and e["access_time"].endswith("Z") and _dp4.after_hours(e["access_time"]))
    print(f"Uploaded s3://{_dp4.BUCKET}/{key}  events={len(events)}  bad={bad}  after-hours granted={ah}")


def recent_file(rng, now, minutes=60, n=None):
    reader = _dp4.random_reader(rng)
    n = n or rng.randint(3, 12)
    times = sorted(now - timedelta(seconds=rng.randint(0, minutes * 60)) for _ in range(n))
    return reader, [_dp4.event(reader, t, rng.choice(_dp4.USERS), "denied" if rng.random() < 0.07 else "granted", rng)
                    for t in times]


def cmd_normal(a, rng, s3):
    now = datetime.now(timezone.utc)
    for _ in range(a.files):
        reader, events = recent_file(rng, now)
        key = _dp4.new_key(reader, rng=rng)
        _dp4.upload(key, _dp4.dumps(_dp4.document(reader, events)), s3)
        summary(key, events)


def cmd_day(a, rng, s3):
    if a.date == _dp4.CHECK_DATE:
        sys.exit(f"{_dp4.CHECK_DATE} is reserved for kit/check_project.py. Choose another date.")
    total = 0
    for _ in range(a.files):
        reader = _dp4.random_reader(rng)
        times = _dp4.day_times(a.date, rng.randint(5, 25), rng)
        events = [_dp4.event(reader, t, rng.choice(_dp4.USERS), "denied" if rng.random() < 0.07 else "granted", rng)
                  for t in times]
        key = _dp4.new_key(reader, rng=rng)
        _dp4.upload(key, _dp4.dumps(_dp4.document(reader, events)), s3)
        total += len(events)
    print(f"Uploaded {a.files} files with {total} events on {a.date}.")


def load_copy(key):
    path = _dp4.local_copy(key)
    if not path.exists():
        sys.exit(f"No local copy of {key} in out/. Copy the key exactly from an 'Uploaded s3://...' line.")
    return path.read_text(encoding="utf-8")


def cmd_again(a, rng, s3):
    body = load_copy(a.key)
    _dp4.upload(a.key, body, s3)
    print(f"Uploaded the same file again: s3://{_dp4.BUCKET}/{a.key}")


def cmd_retry(a, rng, s3):
    doc = json.loads(load_copy(a.key))
    key = _dp4.new_key(doc["reader"], rng=rng)
    doc["uploaded_at"] = _dp4.iso(datetime.now(timezone.utc))
    _dp4.upload(key, _dp4.dumps(doc), s3)
    print(f"Reader {doc['reader']} retried: the {len(doc['events'])} events of {a.key} uploaded again as")
    summary(key, doc["events"])


def bad_rows(reader, rng, now):
    """One event per rule, each breaking exactly that rule."""
    def ev():
        return _dp4.event(reader, now - timedelta(minutes=rng.randint(1, 50)), rng.choice(_dp4.USERS), "granted", rng)
    rows = [ev() for _ in range(6)]
    rows[0].pop("user_identity")                                   # R1 missing field
    rows[1]["building_code"] = "Z99"                               # R2 unknown building
    rows[2]["building_door_id"] = "7"                              # R3 door not 10-69
    rows[3]["user_identity"] = "Student 42"                        # R4 not a computing ID
    rows[4]["access_time"] = _dp4.iso(now + timedelta(hours=3))    # R5 in the future
    rows[5]["result"] = "maybe"                                    # R6 unknown result
    return rows


def cmd_bad(a, rng, s3):
    now = datetime.now(timezone.utc)
    reader, good = recent_file(rng, now, n=10)
    events = good + bad_rows(reader, rng, now)
    rng.shuffle(events)
    key = _dp4.new_key(reader, rng=rng)
    _dp4.upload(key, _dp4.dumps(_dp4.document(reader, events)), s3)
    summary(key, events, bad=6)


def cmd_broken(a, rng, s3):
    reader, events = recent_file(rng, datetime.now(timezone.utc))
    body = _dp4.dumps(_dp4.document(reader, events))
    key = _dp4.new_key(reader, rng=rng)
    _dp4.upload(key, body[: len(body) // 2], s3)
    print(f"Uploaded s3://{_dp4.BUCKET}/{key}  (cut in half: not valid JSON)")


def cmd_burst(a, rng, s3):
    now, total, t0 = datetime.now(timezone.utc), 0, time.perf_counter()
    for _ in range(a.files):
        reader, events = recent_file(rng, now)
        _dp4.upload(_dp4.new_key(reader, rng=rng), _dp4.dumps(_dp4.document(reader, events)), s3)
        total += len(events)
    print(f"Burst: {a.files} files, {total} events uploaded in {time.perf_counter() - t0:.1f} s.")


def cmd_late(a, rng, s3):
    then = datetime.now(timezone.utc) - timedelta(hours=a.hours)
    reader, events = recent_file(rng, then, minutes=30)
    key = _dp4.new_key(reader, rng=rng)
    _dp4.upload(key, _dp4.dumps(_dp4.document(reader, events)), s3)
    summary(key, events)
    print(f"These events happened on {events[0]['access_time'][:10]}, about {a.hours} hours before this upload.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--seed", type=int, help="same files every time")
    sub = p.add_subparsers(dest="cmd", required=True)
    _add = sub.add_parser
    sub.add_parser = lambda name, **kw: _add(name, parents=[common], **kw)
    s = sub.add_parser("normal"); s.add_argument("--files", type=int, default=5); s.set_defaults(fn=cmd_normal)
    s = sub.add_parser("day"); s.add_argument("date"); s.add_argument("--files", type=int, default=40); s.set_defaults(fn=cmd_day)
    s = sub.add_parser("again"); s.add_argument("key"); s.set_defaults(fn=cmd_again)
    s = sub.add_parser("retry"); s.add_argument("key"); s.set_defaults(fn=cmd_retry)
    sub.add_parser("bad").set_defaults(fn=cmd_bad)
    sub.add_parser("broken").set_defaults(fn=cmd_broken)
    s = sub.add_parser("burst"); s.add_argument("--files", type=int, default=200); s.set_defaults(fn=cmd_burst)
    s = sub.add_parser("late"); s.add_argument("--hours", type=int, default=30); s.set_defaults(fn=cmd_late)
    a = p.parse_args()
    rng = random.Random(a.seed)
    s3 = _dp4._aws.client("s3")
    try:
        a.fn(a, rng, s3)
    except s3.exceptions.NoSuchBucket:
        sys.exit(f"Bucket {_dp4.BUCKET} does not exist. Run: python kit/stack.py create")


if __name__ == "__main__":
    main()
