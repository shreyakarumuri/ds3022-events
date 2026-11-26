"""Session 2: read every shard once from the oldest record (TRIM_HORIZON) and summarise.
Adapted from Neal's learn-kinesis/iot-consumer.py. Nothing is stored or checkpointed:
run it twice and it reads everything twice (Kinesis never deletes records you read).

    python s2_kinesis/peek.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _aws  # noqa: E402

STREAM = "sensors"


def main():
    k = _aws.client("kinesis")
    devices_per_shard = defaultdict(Counter)
    for sh in k.list_shards(StreamName=STREAM)["Shards"]:
        it = k.get_shard_iterator(StreamName=STREAM, ShardId=sh["ShardId"],
                                  ShardIteratorType="TRIM_HORIZON")["ShardIterator"]
        while it:
            resp = k.get_records(ShardIterator=it, Limit=1000)
            for r in resp["Records"]:
                try:
                    device = json.loads(r["Data"])["device_id"]
                except (ValueError, KeyError, TypeError):
                    device = "(malformed)"
                devices_per_shard[sh["ShardId"]][device] += 1
            # an open shard always returns a next iterator: stop when we are caught up
            if resp.get("MillisBehindLatest", 0) == 0 and not resp["Records"]:
                break
            it = resp.get("NextShardIterator")
    for shard, c in sorted(devices_per_shard.items()):
        print(f"{shard}: {sum(c.values())} records from {len(c)} devices: {', '.join(sorted(c))}")
    shard_sets = [set(c) - {"(malformed)"} for c in devices_per_shard.values()]
    overlap = {d for d in set().union(*shard_sets) if sum(d in s for s in shard_sets) > 1} if shard_sets else set()
    print(f"Devices found on more than one shard: {sorted(overlap) or 'none'}")


if __name__ == "__main__":
    main()
