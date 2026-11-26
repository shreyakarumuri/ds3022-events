"""Session 1: every change to a DynamoDB item is an event (DynamoDB Streams).

SensorReadings was created with a stream (NEW_AND_OLD_IMAGES). This script reads
the stream from the beginning, then keeps polling for new changes. Run it in T2,
then put/delete items from T3 and watch INSERT / MODIFY / REMOVE appear.

    python s1_dynamodb/watch_changes.py

On AWS, a Lambda function can be triggered by this stream: this loop is what the
Lambda service runs for you (Session 2 builds the same loop for Kinesis).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _aws  # noqa: E402

TABLE = "SensorReadings"


def plain(image):
    """{'temperature': {'N': '21.5'}} -> {'temperature': '21.5'} (DynamoDB JSON to plain values)."""
    if not image:
        return None
    return {k: list(v.values())[0] for k, v in image.items()}


def main():
    arn = _aws.client("dynamodb").describe_table(TableName=TABLE)["Table"].get("LatestStreamArn")
    if not arn:
        sys.exit("SensorReadings has no stream. Recreate it with sensor_table.py create.")
    streams = _aws.client("dynamodbstreams")
    shards = streams.describe_stream(StreamArn=arn)["StreamDescription"]["Shards"]
    iterators = {
        s["ShardId"]: streams.get_shard_iterator(StreamArn=arn, ShardId=s["ShardId"],
                                                 ShardIteratorType="TRIM_HORIZON")["ShardIterator"]
        for s in shards
    }
    print(f"Watching {TABLE} ({len(shards)} stream shard(s)). Ctrl+C to stop.")
    seen = last = 0
    while True:
        for shard_id, it in list(iterators.items()):
            if it is None:
                continue
            resp = streams.get_records(ShardIterator=it, Limit=100)
            for r in resp["Records"]:
                seen += 1
                d = r["dynamodb"]
                key = plain(d["Keys"])
                old, new = plain(d.get("OldImage")), plain(d.get("NewImage"))
                if seen <= 5 or r["eventName"] != "INSERT":
                    print(f"{r['eventName']:<7} {key['device_id']} {key['timestamp']}  old={old and old.get('temperature')}  new={new and new.get('temperature')}")
                elif seen == 6:
                    print("        ... (further INSERTs counted, not printed)")
            iterators[shard_id] = resp.get("NextShardIterator")
        if seen != last:
            print(f"        ({seen} change events so far)")
            last = seen
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
