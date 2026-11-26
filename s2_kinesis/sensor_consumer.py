"""Session 2: a Kinesis consumer that remembers where it stopped.

Adapted from Neal's learn-kinesis/shard-consumer.py, with three changes:
  1. it reads all shards in turn (Neal's version loops forever on the first shard);
  2. each reading is written to the SensorReadings table from Session 1;
  3. a record that is not valid JSON is counted and skipped, never retried forever.

Checkpoints (the last sequence number processed per shard) live in the DynamoDB
table kinesis_checkpoints. Restart the consumer and it resumes AFTER the checkpoint.

    python s2_kinesis/sensor_consumer.py
    python s2_kinesis/sensor_consumer.py --checkpoint-every 50
    python s2_kinesis/sensor_consumer.py --crash-after 37     # card A: exit without a final checkpoint
    python s2_kinesis/sensor_consumer.py --reset              # forget the checkpoints, start from TRIM_HORIZON
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _aws  # noqa: E402

from botocore.exceptions import ClientError  # noqa: E402

STREAM = "sensors"
CHECKPOINTS = "kinesis_checkpoints"
READINGS = "SensorReadings"

kinesis = _aws.client("kinesis")
dynamodb = _aws.resource("dynamodb")


# ---------- checkpoints ----------

def checkpoint_table():
    try:
        t = dynamodb.create_table(
            TableName=CHECKPOINTS,
            KeySchema=[{"AttributeName": "shard_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "shard_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        t.wait_until_exists()
        print(f"Created checkpoint table {CHECKPOINTS}")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceInUseException":
            raise
    return dynamodb.Table(CHECKPOINTS)


def load_checkpoint(table, shard_id):
    return table.get_item(Key={"shard_id": shard_id}).get("Item", {}).get("sequence_number")


def save_checkpoint(table, shard_id, seq):
    table.put_item(Item={"shard_id": shard_id, "sequence_number": seq,
                         "updated_at": datetime.now(timezone.utc).isoformat()})
    print(f"    checkpoint {shard_id} @ {seq}")


def iterator_for(shard_id, seq):
    if seq:
        return kinesis.get_shard_iterator(StreamName=STREAM, ShardId=shard_id,
                                          ShardIteratorType="AFTER_SEQUENCE_NUMBER",
                                          StartingSequenceNumber=seq)["ShardIterator"]
    return kinesis.get_shard_iterator(StreamName=STREAM, ShardId=shard_id,
                                      ShardIteratorType="TRIM_HORIZON")["ShardIterator"]


# ---------- processing ----------

def process(record, readings, stats):
    """Deserialise one record and upsert it. Same key = same item: a replay overwrites, it does not duplicate."""
    try:
        reading = json.loads(record["Data"], parse_float=Decimal)  # DynamoDB wants Decimal, not float
        if not isinstance(reading, dict) or "device_id" not in reading or "timestamp" not in reading:
            raise ValueError("missing key fields")
    except (ValueError, UnicodeDecodeError) as e:
        stats["malformed"] += 1
        print(f"    skipped malformed record seq={record['SequenceNumber']} ({e})")
        return
    readings.put_item(Item=reading)
    stats["written"] += 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint-every", type=int, default=10)
    p.add_argument("--crash-after", type=int, default=0)
    p.add_argument("--reset", action="store_true")
    args = p.parse_args()

    cps = checkpoint_table()
    readings = dynamodb.Table(READINGS)
    shards = [s["ShardId"] for s in kinesis.list_shards(StreamName=STREAM)["Shards"]]
    if args.reset:
        for s in shards:
            cps.delete_item(Key={"shard_id": s})
        print("Checkpoints deleted.")
    state = {}
    for s in shards:
        seq = load_checkpoint(cps, s)
        print(f"{s}: " + (f"resuming after {seq}" if seq else "no checkpoint, starting at TRIM_HORIZON"))
        state[s] = {"it": iterator_for(s, seq), "last": seq, "since": 0}

    stats = {"written": 0, "malformed": 0}
    try:
        while True:
            got = 0
            for s, st in list(state.items()):  # round robin: one GetRecords call per shard per pass
                resp = kinesis.get_records(ShardIterator=st["it"], Limit=100)
                for r in resp["Records"]:
                    process(r, readings, stats)
                    st["last"], st["since"] = r["SequenceNumber"], st["since"] + 1
                    got += 1
                    done = stats["written"] + stats["malformed"]
                    if args.crash_after and done >= args.crash_after:
                        print(f"CRASH after {done} records (last checkpoint not updated)")
                        sys.exit(1)
                    if st["since"] >= args.checkpoint_every:
                        save_checkpoint(cps, s, st["last"])
                        st["since"] = 0
                if resp.get("NextShardIterator") is None:  # shard closed by a reshard (real AWS)
                    if st["last"]:
                        save_checkpoint(cps, s, st["last"])
                    print(f"  {s} is closed and fully read. Restart the consumer to pick up the new shards.")
                    del state[s]
                else:
                    st["it"] = resp["NextShardIterator"]
            if got:
                print(f"  processed {got:>4} this pass | written {stats['written']}  malformed {stats['malformed']}")
            else:
                time.sleep(1)  # caught up: real AWS allows 5 GetRecords calls per shard per second
    except KeyboardInterrupt:
        for s, st in state.items():  # clean stop: save where every shard got to
            if st["last"] and st["since"]:
                save_checkpoint(cps, s, st["last"])
        print(f"\nStopped. {stats}")


if __name__ == "__main__":
    main()
