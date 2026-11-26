"""Session 3: test the function without deploying it and without the emulator running.

moto's mock_aws fakes AWS inside this process; Chalice's test client builds an S3
event and invokes the handler, as in Neal's tests/test_app.py.

    cd s3_lambda/sensor-files
    pytest -q
"""
import json
import os

import boto3
import pytest
from moto import mock_aws

BUCKET = "test-bucket"
os.environ.pop("AWS_ENDPOINT_URL", None)  # in-process fake: no endpoint
os.environ.update({"APP_BUCKET_NAME": BUCKET, "READINGS_TABLE": "Readings", "FILELOG_TABLE": "FileLog",
                   "AWS_DEFAULT_REGION": "us-east-1", "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"})

from chalice.test import Client  # noqa: E402
from chalicelib import validate  # noqa: E402


def make_tables():
    ddb = boto3.client("dynamodb")
    ddb.create_table(TableName="Readings", BillingMode="PAY_PER_REQUEST",
                     AttributeDefinitions=[{"AttributeName": "device_id", "AttributeType": "S"},
                                           {"AttributeName": "timestamp", "AttributeType": "S"}],
                     KeySchema=[{"AttributeName": "device_id", "KeyType": "HASH"},
                                {"AttributeName": "timestamp", "KeyType": "RANGE"}])
    ddb.create_table(TableName="FileLog", BillingMode="PAY_PER_REQUEST",
                     AttributeDefinitions=[{"AttributeName": "file_key", "AttributeType": "S"}],
                     KeySchema=[{"AttributeName": "file_key", "KeyType": "HASH"}])


@pytest.fixture
def aws(monkeypatch):
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)  # never send test traffic to a running emulator
    with mock_aws():
        boto3.client("s3").create_bucket(Bucket=BUCKET)
        make_tables()
        import app as app_module  # import inside the mock so its boto3 clients are faked
        yield app_module


def good(i):
    return {"device_id": "sensor-001", "timestamp": f"2026-11-26T14:00:{i:02d}Z", "temperature": 70 + i}


def drop(client, key, body):
    boto3.client("s3").put_object(Bucket=BUCKET, Key=key, Body=body)
    event = client.events.generate_s3_event(bucket=BUCKET, key=key)
    return client.lambda_.invoke("on_file", event).payload


def count(table):
    return boto3.resource("dynamodb").Table(table).scan()["Count"]


def test_good_file_is_stored(aws):
    with Client(aws.app, stage_name="dev") as client:
        result = drop(client, "uploads/a.json", json.dumps({"readings": [good(i) for i in range(5)]}))
    assert result["status"] == "ok" and result["valid"] == 5
    assert count("Readings") == 5


def test_same_file_twice_does_not_duplicate(aws):
    body = json.dumps({"readings": [good(i) for i in range(5)]})
    with Client(aws.app, stage_name="dev") as client:
        drop(client, "uploads/a.json", body)
        drop(client, "uploads/a.json", body)
    assert count("Readings") == 5
    assert count("FileLog") == 1


def test_bad_rows_are_rejected_not_stored(aws):
    rows = [good(1), {**good(2), "temperature": 999}, {"timestamp": "2026-11-26T14:00:03Z", "temperature": 1}]
    with Client(aws.app, stage_name="dev") as client:
        result = drop(client, "uploads/b.json", json.dumps({"readings": rows}))
    assert result["status"] == "partial" and result["valid"] == 1 and result["rejected"] == 2


def test_broken_json_does_not_raise(aws):
    with Client(aws.app, stage_name="dev") as client:
        result = drop(client, "uploads/c.json", '{"readings": [')
    assert result["status"] == "rejected"
    assert count("Readings") == 0


def test_api_returns_newest_first(aws):
    with Client(aws.app, stage_name="dev") as client:
        drop(client, "uploads/a.json", json.dumps({"readings": [good(i) for i in range(5)]}))
        resp = client.http.get("/devices/sensor-001/readings?limit=2")
    body = json.loads(resp.body)
    assert resp.status_code == 200 and body["count"] == 2
    assert body["readings"][0]["timestamp"] == "2026-11-26T14:00:04Z"


@pytest.mark.parametrize("reading, reason", [
    ({"timestamp": "2026-11-26T14:00:00Z", "temperature": 1}, "missing device_id"),
    ({"device_id": "sensor-1", "timestamp": "2026-11-26T14:00:00Z", "temperature": 1}, "bad device_id"),
    ({"device_id": "sensor-001", "timestamp": "yesterday", "temperature": 1}, "timestamp is not ISO 8601"),
    ({"device_id": "sensor-001", "timestamp": "2026-11-26T14:00:00", "temperature": 1}, "timestamp has no time zone"),
    ({"device_id": "sensor-001", "timestamp": "2026-11-26T14:00:00Z", "temperature": "warm"}, "temperature is not a number"),
    ({"device_id": "sensor-001", "timestamp": "2026-11-26T14:00:00Z", "temperature": 999}, "temperature out of range (-40 to 150 F)"),
])
def test_validation_rules(reading, reason):
    assert validate.check(reading) == reason
