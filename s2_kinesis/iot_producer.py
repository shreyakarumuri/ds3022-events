"""Session 2: IoT sensors write readings to Kinesis (adapted from Neal's learn-kinesis/iot-producer.py).

    python s2_kinesis/iot_producer.py                  # 5 readings/s from 10 devices, until Ctrl+C
    python s2_kinesis/iot_producer.py --rate 20 --count 600
    python s2_kinesis/iot_producer.py --bad-every 50   # every 50th record is not valid JSON (card B)
    python s2_kinesis/iot_producer.py --key random     # card C: a random partition key per record

Partition key = device_id: every reading of one device goes to the same shard,
so a consumer sees each device's readings in order (the Kafka key, again).
"""
import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _aws  # noqa: E402

STREAM = "sensors"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rate", type=float, default=5, help="records per second")
    p.add_argument("--devices", type=int, default=10)
    p.add_argument("--count", type=int, default=0, help="stop after N records (0 = run until Ctrl+C)")
    p.add_argument("--bad-every", type=int, default=0)
    p.add_argument("--key", choices=["device", "random"], default="device")
    args = p.parse_args()
    devices = [f"sensor-{i:03d}" for i in range(1, args.devices + 1)]
    k = _aws.client("kinesis")
    per_shard, n = {}, 0
    try:
        while not args.count or n < args.count:
            device = random.choice(devices)
            record = {
                "device_id": device,
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "temperature": round(random.gauss(72, 5), 2),
                "humidity": round(random.uniform(30, 80), 2),
                "pressure": round(random.gauss(1013, 10), 2),
            }
            data = json.dumps(record)
            if args.bad_every and (n + 1) % args.bad_every == 0:
                data = "this is not a sensor reading"
            key = device if args.key == "device" else str(uuid.uuid4())
            resp = k.put_record(StreamName=STREAM, Data=data, PartitionKey=key)
            n += 1
            per_shard[resp["ShardId"]] = per_shard.get(resp["ShardId"], 0) + 1
            print(f"{n:>5}  {device} -> {resp['ShardId']}  seq={resp['SequenceNumber']}")
            time.sleep(1 / args.rate)
    except KeyboardInterrupt:
        pass
    print(f"\nSent {n} records. Per shard: {per_shard}")


if __name__ == "__main__":
    main()
