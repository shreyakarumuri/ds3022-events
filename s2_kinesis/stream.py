"""Session 2: create, inspect and delete the Kinesis data stream.

    python s2_kinesis/stream.py create            # stream 'sensors' with 2 shards
    python s2_kinesis/stream.py create --shards 4
    python s2_kinesis/stream.py describe          # shards and their hash-key ranges
    python s2_kinesis/stream.py delete
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _aws  # noqa: E402

STREAM = "sensors"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["create", "describe", "delete"])
    p.add_argument("--shards", type=int, default=2)
    args = p.parse_args()
    k = _aws.client("kinesis")
    if args.cmd == "create":
        k.create_stream(StreamName=STREAM, ShardCount=args.shards)  # provisioned mode: you choose shards
        k.get_waiter("stream_exists").wait(StreamName=STREAM)
        print(f"Stream {STREAM} ACTIVE with {args.shards} shards.")
    if args.cmd in ("create", "describe"):
        s = k.describe_stream_summary(StreamName=STREAM)["StreamDescriptionSummary"]
        print(f"Status {s['StreamStatus']}, retention {s['RetentionPeriodHours']} h, open shards {s['OpenShardCount']}")
        for sh in k.list_shards(StreamName=STREAM)["Shards"]:
            if "EndingSequenceNumber" in sh["SequenceNumberRange"]:
                print(f"  {sh['ShardId']}  CLOSED: no new records; still readable until retention ends")
                continue
            r = sh["HashKeyRange"]
            share = (int(r["EndingHashKey"]) - int(r["StartingHashKey"]) + 1) / 2**128
            print(f"  {sh['ShardId']}  owns {share:.0%} of the MD5 hash space of partition keys")
    if args.cmd == "delete":
        k.delete_stream(StreamName=STREAM)
        print(f"Deleted {STREAM}.")


if __name__ == "__main__":
    main()
