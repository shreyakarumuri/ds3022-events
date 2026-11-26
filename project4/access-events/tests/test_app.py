"""Data Project 4 tests. Run from the access-events folder:  pytest -q

The fixture in conftest.py fakes AWS in this process (no emulator needed) and creates
the tables from YOUR template.yaml, so the tests follow your key design.
Two examples are given; checkpoint E asks for at least 8 tests in total, including
one per rule (R2 to R6), one for idempotency and one per route.
"""
import json

import boto3
from chalice.test import Client

from chalicelib import validate  # noqa: F401  (for your rule tests)
from tests.conftest import APP_DIR, BUCKET


def ev(i, **change):
    e = {"event_id": f"J10-11-test-{i}", "building_code": "J10", "building_door_id": "11",
         "user_identity": "mst3k", "access_time": f"2026-11-09T09:00:{i:02d}Z", "result": "granted"}
    e.update(change)
    return e


def doc(events):
    return json.dumps({"reader": "J10-11", "uploaded_at": "2026-11-09T09:01:00Z", "events": events})


def drop(client, key, body):
    boto3.client("s3").put_object(Bucket=BUCKET, Key=key, Body=body)
    return client.lambda_.invoke("on_file", client.events.generate_s3_event(bucket=BUCKET, key=key)).payload


def test_good_file_is_logged_ok(aws):
    with Client(aws.app, stage_name="dev", project_dir=str(APP_DIR)) as c:
        result = drop(c, "uploads/a.json", doc([ev(i) for i in range(3)]))
        files = json.loads(c.http.get("/files").body)
    assert result["status"] == "ok"
    assert files[0]["file_key"] == "uploads/a.json" and files[0]["valid"] == 3


def test_broken_json_is_rejected_not_raised(aws):
    with Client(aws.app, stage_name="dev", project_dir=str(APP_DIR)) as c:
        result = drop(c, "uploads/b.json", '{"events": [')
    assert result["status"] == "rejected"


# TODO E: at least 6 more tests. Suggestions:
#   one per rule R2..R6 (validate.check with now=... fixed, assert the reason starts with "R<n>")
#   the same file twice -> P1 count unchanged; an event repeated inside one file
#   P1 order and the 400 without a date; P2 newest first with limit; P3 found and 404
#   a +01:00 time stored and returned in UTC
