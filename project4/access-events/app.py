"""Data Project 4: badge-reader files -> Lambda (Chalice) -> DynamoDB -> API.

Start from what you built on Mon 23 Nov (ds3022-events/s3_lambda/sensor-files/app.py):
the structure is the same. The API contract (paths, parameters, JSON shapes, status
codes) is in BRIEF.md: kit/check_project.py checks it exactly.

Keep the function name on_file: kit/local_lambda.py calls it.
"""
import json
import logging
import os
from datetime import datetime, timezone

import boto3
from chalice import BadRequestError, Chalice, NotFoundError  # noqa: F401  (you will need them)

from chalicelib import model, validate

app = Chalice(app_name="access-events")
app.log.setLevel(logging.INFO)

BUCKET = os.environ.get("APP_BUCKET_NAME", "")
ACCESS_TABLE = os.environ.get("ACCESS_TABLE", "access")
FILELOG_TABLE = os.environ.get("FILELOG_TABLE", "file_log")

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


@app.on_s3_event(bucket=BUCKET, events=["s3:ObjectCreated:*"], suffix=".json")
def on_file(event):
    """One uploaded file. Bad DATA is recorded and the function returns normally;
    a broken INFRASTRUCTURE call raises, so the event is retried (and ends in the DLQ)."""
    key = event.key
    app.log.info(f"New object s3://{event.bucket}/{key}")
    # TODO B1: read the object and deserialise it; a file that is not JSON -> log_file(..., "rejected", ...) and return
    # TODO B2: validate.split(document) -> valid events (normalised) and rejected rows
    # TODO B3: write every valid event with the items from your key design (model.py).
    #          The same event can arrive twice: in a re-uploaded file, in a retry file, even twice in one file.
    # TODO B4: log_file(key, status, ...) with status ok / partial / rejected, and return a small summary dict
    raise NotImplementedError("on_file")


def log_file(key, status, valid, rejected):
    """One row per file in file_log (given: same as Mon 23 Nov)."""
    dynamodb.Table(FILELOG_TABLE).put_item(Item={
        "file_key": key,
        "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "valid": valid,
        "rejected": len(rejected),
        "reasons": [r["reason"] for r in rejected][:10],
    })


@app.route("/buildings/{code}/access", methods=["GET"])
def building_access(code):
    """P1. ?date=YYYY-MM-DD required (400 without it). Every access to the building that UTC day, oldest first."""
    raise NotImplementedError("P1")  # TODO D1


@app.route("/buildings/{code}/after-hours", methods=["GET"])
def building_after_hours(code):
    """Granted accesses that UTC day between 22:00 and 06:00 UTC, oldest first."""
    raise NotImplementedError("after-hours")  # TODO D2


@app.route("/users/{user}/access", methods=["GET"])
def user_access(user):
    """P2. ?limit=N (default 10, at most 100). The user's latest accesses, newest first."""
    raise NotImplementedError("P2")  # TODO D3


@app.route("/events/{event_id}", methods=["GET"])
def get_event(event_id):
    """P3. One event by its id; 404 (NotFoundError) if it does not exist."""
    raise NotImplementedError("P3")  # TODO D4


@app.route("/files", methods=["GET"])
def files():
    """Given: the processing log, newest first (small table: a Scan is acceptable here)."""
    items = dynamodb.Table(FILELOG_TABLE).scan()["Items"]
    out = [{k: (int(v) if k in ("valid", "rejected") else v) for k, v in i.items()} for i in items]
    return sorted(out, key=lambda x: x["processed_at"], reverse=True)
