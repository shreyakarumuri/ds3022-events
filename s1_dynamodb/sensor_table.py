"""Session 1: DynamoDB basics on one table (adapted from Neal's learn-dynamodb/python).

Table SensorReadings
  partition key (HASH):  device_id   which drawer of the filing cabinet
  sort key     (RANGE):  timestamp   order of the folders inside the drawer
Only the two key attributes are declared. Everything else is added when you write.

Usage (from the repo root, emulator running in T1):
    python s1_dynamodb/sensor_table.py create
    python s1_dynamodb/sensor_table.py put sensor-001 21.5
    python s1_dynamodb/sensor_table.py get sensor-001 2026-11-19T14:00:00Z
    python s1_dynamodb/sensor_table.py batch 500
    python s1_dynamodb/sensor_table.py query sensor-003 --latest 5
    python s1_dynamodb/sensor_table.py query sensor-003 --since 2026-11-19T15:00:00Z
    python s1_dynamodb/sensor_table.py scan
    python s1_dynamodb/sensor_table.py scan --hot 80
    python s1_dynamodb/sensor_table.py scan --hot 80 --page 100
    python s1_dynamodb/sensor_table.py delete sensor-001 2026-11-19T14:00:00Z
    python s1_dynamodb/sensor_table.py count
"""
import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _aws  # noqa: E402

from boto3.dynamodb.conditions import Attr, Key  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

TABLE = "SensorReadings"
DEVICES = [f"sensor-{i:03d}" for i in range(1, 6)]


def table():
    return _aws.resource("dynamodb").Table(TABLE)


def create(args):
    ddb = _aws.client("dynamodb")
    try:
        ddb.create_table(
            TableName=TABLE,
            AttributeDefinitions=[
                {"AttributeName": "device_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "device_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
            # Every change to an item becomes an event (watch_changes.py reads them).
            StreamSpecification={"StreamEnabled": True, "StreamViewType": "NEW_AND_OLD_IMAGES"},
        )
        print(f"Creating table {TABLE} ...")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"Table {TABLE} already exists.")
            return
        raise
    ddb.get_waiter("table_exists").wait(TableName=TABLE)
    print(f"Table {TABLE} is ACTIVE.")


def put(args):
    ts = args.ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    item = {
        "device_id": args.device,
        "timestamp": ts,
        # DynamoDB numbers must be Decimal in boto3, never float.
        "temperature": Decimal(str(args.temperature)),
        "status": "ok",
    }
    table().put_item(Item=item)
    print(f"Put {item}")


def get(args):
    resp = table().get_item(Key={"device_id": args.device, "timestamp": args.ts})
    print(resp.get("Item", "No item with that full primary key."))


def batch(args):
    """Seeded readings: same data on every laptop. One reading per device per minute."""
    rng = random.Random(3022)
    start = datetime(2026, 11, 18, 14, 0, tzinfo=timezone.utc)  # yesterday afternoon (class day: Thu 19 Nov)
    n = 0
    with table().batch_writer() as bw:  # groups puts into calls of up to 25 items
        for minute in range(args.n // len(DEVICES)):
            ts = (start + timedelta(minutes=minute)).strftime("%Y-%m-%dT%H:%M:%SZ")
            for d in DEVICES:
                temp = round(rng.gauss(72, 5), 2)
                if rng.random() < 0.02:
                    temp = round(rng.uniform(85, 95), 2)  # a few hot spikes to find later
                bw.put_item(Item={
                    "device_id": d,
                    "timestamp": ts,
                    "temperature": Decimal(str(temp)),
                    "humidity": Decimal(str(round(rng.uniform(30, 80), 2))),
                    "status": "ok",
                })
                n += 1
    print(f"Wrote {n} readings for {len(DEVICES)} devices starting {start:%Y-%m-%d %H:%M} UTC.")


def query(args):
    cond = Key("device_id").eq(args.device)
    if args.since:
        cond = cond & Key("timestamp").gt(args.since)
    kwargs = {"KeyConditionExpression": cond, "ScanIndexForward": False}  # newest first
    if args.latest:
        kwargs["Limit"] = args.latest
    resp = table().query(**kwargs)
    for it in resp["Items"]:
        print(f"  {it['timestamp']}  temp={it.get('temperature')}")
    print(f"Query: Count={resp['Count']}  ScannedCount={resp['ScannedCount']}")


def scan(args):
    kwargs = {"Limit": args.page} if args.page else {}  # Limit = items READ per page
    if args.hot is not None:
        kwargs["FilterExpression"] = Attr("temperature").gt(Decimal(str(args.hot)))
    items, scanned, pages = [], 0, 0
    while True:  # a Scan is paginated: follow LastEvaluatedKey until it disappears
        resp = table().scan(**kwargs)
        items += resp["Items"]
        scanned += resp["ScannedCount"]
        pages += 1
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    for it in sorted(items, key=lambda x: x["timestamp"])[:10]:
        print(f"  {it['device_id']}  {it['timestamp']}  temp={it.get('temperature')}")
    print(f"Scan: returned={len(items)}  read (ScannedCount)={scanned}  pages={pages}")


def delete(args):
    table().delete_item(Key={"device_id": args.device, "timestamp": args.ts})
    print(f"Deleted {args.device} {args.ts} (no error even if it did not exist).")


def count(args):
    print(_aws.client("dynamodb").describe_table(TableName=TABLE)["Table"].get("ItemCount"),
          "(ItemCount is refreshed about every 6 hours on real AWS)")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("create").set_defaults(fn=create)
    s = sub.add_parser("put"); s.add_argument("device"); s.add_argument("temperature", type=float)
    s.add_argument("--ts"); s.set_defaults(fn=put)
    s = sub.add_parser("get"); s.add_argument("device"); s.add_argument("ts"); s.set_defaults(fn=get)
    s = sub.add_parser("batch"); s.add_argument("n", type=int, nargs="?", default=500); s.set_defaults(fn=batch)
    s = sub.add_parser("query"); s.add_argument("device"); s.add_argument("--since")
    s.add_argument("--latest", type=int); s.set_defaults(fn=query)
    s = sub.add_parser("scan"); s.add_argument("--hot", type=float)
    s.add_argument("--page", type=int, help="items read per request (real AWS: 1 MB per page)"); s.set_defaults(fn=scan)
    s = sub.add_parser("delete"); s.add_argument("device"); s.add_argument("ts"); s.set_defaults(fn=delete)
    sub.add_parser("count").set_defaults(fn=count)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
