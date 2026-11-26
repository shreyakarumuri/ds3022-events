"""Session 3: make a sensor file and drop it into the bucket (the event that starts everything).

Serialisation practice from the JSON/REST lab: a Reading class holds a real
datetime; a custom JSONEncoder turns it into ISO 8601 text when the file is written.

    python s3_lambda/drop_file.py                     # 20 good readings from one device
    python s3_lambda/drop_file.py --n 50 --device sensor-007
    python s3_lambda/drop_file.py --bad 3             # card B: 3 readings that break the rules
    python s3_lambda/drop_file.py --broken            # card C: the file is not JSON at all
    python s3_lambda/drop_file.py --suffix .txt       # card D: does a .txt file trigger the function?
    python s3_lambda/drop_file.py --again uploads/sensor-007_20261126T140501.json   # card A: same file twice
"""
import argparse
import json
import random
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _aws  # noqa: E402

BUCKET = "ds3022-sensor-files"
OUT = Path(__file__).resolve().parent.parent / "out"


@dataclass
class Reading:
    device_id: str
    timestamp: datetime
    temperature: float
    humidity: Optional[float] = None


class SensorEncoder(json.JSONEncoder):
    """json.dumps cannot serialise datetime by default: teach it how."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Reading):
            return asdict(obj)
        return super().default(obj)


def make_readings(device, n):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return [Reading(device, now - timedelta(seconds=10 * (n - i)),
                    round(random.gauss(72, 5), 2), round(random.uniform(30, 80), 2)) for i in range(n)]


def break_some(readings, k):
    """Return dicts; k of them violate one rule each."""
    rows = [asdict(r) for r in readings]
    faults = [
        lambda r: r.pop("device_id"),
        lambda r: r.update(temperature=999),
        lambda r: r.update(timestamp="yesterday afternoon"),
        lambda r: r.update(temperature="warm"),
        lambda r: r.update(humidity=140),
    ]
    for i, idx in enumerate(random.sample(range(len(rows)), min(k, len(rows)))):
        faults[i % len(faults)](rows[idx])
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--device", default=f"sensor-{random.randint(1, 10):03d}")
    p.add_argument("--bad", type=int, default=0)
    p.add_argument("--broken", action="store_true")
    p.add_argument("--suffix", default=".json")
    p.add_argument("--again", help="upload this key again with the same content")
    args = p.parse_args()
    s3 = _aws.client("s3")

    if args.again:
        local = OUT / Path(args.again).name
        s3.put_object(Bucket=BUCKET, Key=args.again, Body=local.read_bytes())
        print(f"Uploaded the same file again: s3://{BUCKET}/{args.again}")
        return

    readings = make_readings(args.device, args.n)
    document = {
        "metadata": {"source": "drop_file.py", "created_at": datetime.now(timezone.utc), "count": args.n},
        "readings": break_some(readings, args.bad) if args.bad else readings,
    }
    body = json.dumps(document, cls=SensorEncoder, indent=2)  # serialise: Python objects -> JSON text
    if args.broken:
        body = body[: len(body) // 2]  # cut in half: no longer valid JSON
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    key = f"uploads/{args.device}_{stamp}{args.suffix}"
    OUT.mkdir(exist_ok=True)
    (OUT / Path(key).name).write_text(body, encoding="utf-8")
    s3.put_object(Bucket=BUCKET, Key=key, Body=body.encode("utf-8"), ContentType="application/json")
    print(f"Uploaded s3://{BUCKET}/{key}  ({args.n} readings, {args.bad} bad{', BROKEN JSON' if args.broken else ''})")


if __name__ == "__main__":
    main()
