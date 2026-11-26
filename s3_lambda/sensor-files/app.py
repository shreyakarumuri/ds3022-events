"""Session 3: an event-driven pipeline with AWS Lambda (Chalice).

    new .json file in S3  ->  on_file() (Lambda)  ->  DynamoDB  ->  GET /devices/{id}/readings

Pattern from Neal's Data Project 4 app.py (S3 trigger -> deserialise -> put_item ->
GET route), applied to sensor files, with a data-quality check on arrival.

Locally, local_lambda.py plays the part of the Lambda service and `chalice local`
serves the API. On AWS, `chalice deploy --stage dev` creates the function, the
S3 trigger and the API Gateway endpoint from this same file.
"""
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from chalice import Chalice

from chalicelib import validate

app = Chalice(app_name="sensor-files")
app.log.setLevel(logging.INFO)  # Chalice logs only errors unless told otherwise

# Environment variables come from .chalice/config.json (per stage).
BUCKET = os.environ.get("APP_BUCKET_NAME", "")
READINGS_TABLE = os.environ.get("READINGS_TABLE", "Readings")
FILELOG_TABLE = os.environ.get("FILELOG_TABLE", "FileLog")

# Created once per container (cold start), reused by every warm invocation.
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


@app.on_s3_event(bucket=BUCKET, events=["s3:ObjectCreated:*"], suffix=".json")
def on_file(event):
    app.log.info(f"New object s3://{event.bucket}/{event.key}")
    body = s3.get_object(Bucket=event.bucket, Key=event.key)["Body"].read()  # infrastructure error -> raise -> retried

    try:
        document = json.loads(body, parse_float=Decimal)  # deserialise; DynamoDB needs Decimal, not float
    except (ValueError, UnicodeDecodeError) as e:
        # Bad DATA: retrying cannot fix it. Record it and return normally (no retry).
        log_file(event.key, status="rejected", valid=0, rejected=[{"index": None, "reason": f"not JSON: {e}"[:120]}])
        app.log.warning(f"{event.key}: not valid JSON, file rejected")
        return {"file": event.key, "status": "rejected"}

    valid, rejected = validate.split(document)
    with dynamodb.Table(READINGS_TABLE).batch_writer() as bw:
        for r in valid:
            bw.put_item(Item={**r, "source_file": event.key})  # same (device_id, timestamp) = overwrite: replays are safe
    status = "ok" if not rejected else ("partial" if valid else "rejected")
    log_file(event.key, status=status, valid=len(valid), rejected=rejected)
    app.log.info(f"{event.key}: {len(valid)} stored, {len(rejected)} rejected")
    return {"file": event.key, "status": status, "valid": len(valid), "rejected": len(rejected)}


def log_file(key, status, valid, rejected):
    dynamodb.Table(FILELOG_TABLE).put_item(Item={
        "file_key": key,
        "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "valid": valid,
        "rejected": len(rejected),
        "reasons": [r["reason"] for r in rejected][:10],
    })


@app.route("/devices/{device_id}/readings", methods=["GET"])
def device_readings(device_id):
    params = app.current_request.query_params or {}
    limit = min(int(params.get("limit", 10)), 100)
    resp = dynamodb.Table(READINGS_TABLE).query(
        KeyConditionExpression=Key("device_id").eq(device_id),
        ScanIndexForward=False,  # newest first
        Limit=limit,
    )
    return {"device_id": device_id, "count": resp["Count"], "readings": [plain(i) for i in resp["Items"]]}


@app.route("/files", methods=["GET"])
def files():
    items = dynamodb.Table(FILELOG_TABLE).scan()["Items"]  # small table: a Scan is fine here
    return sorted((plain(i) for i in items), key=lambda x: x["processed_at"], reverse=True)


def plain(item):
    """DynamoDB returns numbers as Decimal: turn them into int/float for an ordinary JSON response."""
    def num(v):
        return int(v) if v == v.to_integral_value() else float(v)
    return {k: num(v) if isinstance(v, Decimal) else v for k, v in item.items()}
