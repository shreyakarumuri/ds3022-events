# ds3022-events: Event-Driven Computing, Sessions 1 to 3

Scripts for the three Event-Driven Computing classes (Thu 19 Nov, Fri 20 Nov, Mon 23 Nov).
Everything runs on your laptop against **Moto**, a local AWS emulator: no AWS account, no credentials, no cost.
Every script calls `boto3` exactly as it would on AWS. The only difference is one line in `.env`
(`AWS_ENDPOINT_URL`); remove it and add real credentials and the same code talks to real AWS.

```
s1_dynamodb/   Session 1 · Thu 19 Nov   DynamoDB tables, keys, Query vs Scan, JSON from a REST API, change events
s2_kinesis/    Session 2 · Fri 20 Nov   Kinesis stream, shards, producer, consumer with checkpoints
s3_lambda/     Session 3 · Mon 23 Nov   S3 file -> Lambda (Chalice) -> DynamoDB -> API, retries and a dead-letter queue
```

## Setup (once, about 5 minutes)

Use Python 3.12 or 3.13.

macOS / Linux:
```bash
cd ds3022-events
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows (PowerShell):
```powershell
cd ds3022-events
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

## Terminals

| Terminal | Runs | Leave it running? |
|---|---|---|
| **T1 · Emulator** | `moto_server -p 9324` | Yes |
| **T2 · Watcher** | the script that waits for events (`watch_changes.py`, `sensor_consumer.py`, `local_lambda.py`) | Yes |
| **T3 · Work** | everything else | It is your working terminal |
| **T4 · API** (Session 3 only) | `chalice local --stage local --port 8000` | Yes |

Activate `.venv` in every terminal. Run every command **from the repo folder** (`ds3022-events`), except the two Chalice commands in Session 3, which run inside `s3_lambda/sensor-files`.

Check the emulator (T3):
```bash
python check_emulator.py
```
You should see five `OK` lines and `Emulator OK`.

The emulator keeps everything **in memory**. If you stop `moto_server`, your tables, streams, buckets and queues disappear. Start it again and re-run the create step of the session.

The emulator's own dashboard shows everything it holds: <http://127.0.0.1:9324/moto-api/>

## Session 1 · Thu 19 Nov
```bash
python s1_dynamodb/sensor_table.py create
python s1_dynamodb/sensor_table.py batch 500
python s1_dynamodb/sensor_table.py query sensor-003 --latest 5
python s1_dynamodb/sensor_table.py scan --hot 80
python s1_dynamodb/github_commits.py fetch boto/boto3 --offline   # the sample file (the instructor does one live fetch)
python s1_dynamodb/github_commits.py load data/commits_boto_boto3.json
python s1_dynamodb/github_commits.py latest boto/boto3 --design a
python s1_dynamodb/github_commits.py latest boto/boto3 --design b
python s1_dynamodb/watch_changes.py                 # finish early: T2, then put/delete in T3
```

## Session 2 · Fri 20 Nov
```bash
python s1_dynamodb/sensor_table.py create          # if the emulator was restarted
python s2_kinesis/stream.py create
python s2_kinesis/iot_producer.py                   # T3, Ctrl+C to stop
python s2_kinesis/peek.py
python s2_kinesis/sensor_consumer.py                # T2
```

## Session 3 · Mon 23 Nov
```bash
python s3_lambda/stack.py create
python s3_lambda/local_lambda.py                    # T2
python s3_lambda/drop_file.py                       # T3
cd s3_lambda/sensor-files
chalice local --stage local --port 8000             # T4, then open http://127.0.0.1:8000/files
pytest -q                                           # tests, no emulator needed
```

## Before you push

`.env`, `.venv/`, `data/` downloads and `out/` are in `.gitignore`. Check with `git status` that none of them is staged.
