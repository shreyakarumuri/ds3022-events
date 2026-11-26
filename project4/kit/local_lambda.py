"""Project 4: play the part of the AWS Lambda service on your laptop. Do not edit.
Same script as Mon 23 Nov (s3_lambda/local_lambda.py), pointed at access-events/.

On AWS, `chalice deploy` connects the bucket to your function and the Lambda
service calls on_file() for every new .json object. The emulator cannot run
Lambda functions, so this script does the same job in four steps:

  1. connect the bucket to a queue: S3 sends an event message for each new .json object
  2. set the function's environment variables from .chalice/config.json, then import app.py (cold start)
  3. wait for event messages and call the handler with each one (warm invocations)
  4. on success delete the message; on an exception leave it, so it comes back and is retried.
     After 3 attempts (Lambda's default for S3: 1 try + 2 retries) it goes to a dead-letter queue.

    python kit/local_lambda.py               # leave running in the Lambda terminal: it is your "CloudWatch Logs"
    python kit/local_lambda.py --show-event  # also print each S3 event exactly as the function receives it
"""
import json
import logging
import os
import sys
import time
from urllib.parse import unquote_plus

import _aws
import _dp4

APP_DIR = _dp4.APP_DIR

STAGE = "local"
QUEUE, DLQ = _dp4.QUEUE, _dp4.DLQ
MAX_ATTEMPTS = 3
VISIBILITY = 10  # seconds before a failed event is tried again (Lambda waits about 1 then 2 minutes)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
logging.getLogger("botocore").setLevel(logging.WARNING)
log = logging.getLogger("local-lambda")


def stage_env():
    config = json.loads((APP_DIR / ".chalice" / "config.json").read_text())
    return config["stages"][STAGE]["environment_variables"]


def wire(bucket):
    """Step 1: the job `chalice deploy` does on AWS (there with Lambda instead of a queue)."""
    sqs, s3 = _aws.client("sqs"), _aws.client("s3")
    q = sqs.create_queue(QueueName=QUEUE, Attributes={"VisibilityTimeout": str(VISIBILITY)})["QueueUrl"]
    dlq = sqs.create_queue(QueueName=DLQ)["QueueUrl"]
    arn = sqs.get_queue_attributes(QueueUrl=q, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    s3.put_bucket_notification_configuration(Bucket=bucket, NotificationConfiguration={"QueueConfigurations": [{
        "QueueArn": arn,
        "Events": ["s3:ObjectCreated:*"],
        "Filter": {"Key": {"FilterRules": [{"Name": "suffix", "Value": ".json"}]}},
    }]})
    log.info(f"Trigger: s3://{bucket} (ObjectCreated, *.json) -> on_file")
    return sqs, q, dlq


def main():
    show = "--show-event" in sys.argv
    env = stage_env()
    os.environ.update(env)  # step 2: the function's environment variables...
    try:
        sqs, q, dlq = wire(env["APP_BUCKET_NAME"])
    except Exception as e:  # noqa: BLE001
        sys.exit(f"Could not connect the bucket: {e}\nIs moto_server running, and did you run  python kit/stack.py create ?")
    sys.path.insert(0, str(APP_DIR))
    t0 = time.perf_counter()
    from app import app  # ...then import your code: the cold start
    from chalice.test import Client
    log.info(f"Cold start: imported app.py in {1000 * (time.perf_counter() - t0):.0f} ms. Waiting for files ...")

    with Client(app, stage_name=STAGE, project_dir=str(APP_DIR)) as client:
        while True:  # step 3
            resp = sqs.receive_message(QueueUrl=q, MaxNumberOfMessages=10, WaitTimeSeconds=10,
                                       AttributeNames=["ApproximateReceiveCount"])
            for m in resp.get("Messages", []):
                event = json.loads(m["Body"])
                if event.get("Event") == "s3:TestEvent":  # S3 sends one when the trigger is first set up
                    sqs.delete_message(QueueUrl=q, ReceiptHandle=m["ReceiptHandle"])
                    continue
                if show:
                    print(json.dumps(event, indent=2))
                attempt = int(m["Attributes"]["ApproximateReceiveCount"])
                key = unquote_plus(event["Records"][0]["s3"]["object"]["key"])  # keys arrive URL-encoded
                start = time.perf_counter()
                try:
                    result = client.lambda_.invoke("on_file", event).payload
                    log.info(f"REPORT {key} attempt {attempt}: {1000 * (time.perf_counter() - start):.0f} ms -> {result}")
                    sqs.delete_message(QueueUrl=q, ReceiptHandle=m["ReceiptHandle"])  # step 4: success
                except Exception as e:  # noqa: BLE001  (an exception in your handler)
                    log.error(f"ERROR {key} attempt {attempt}: {type(e).__name__}: {e}")
                    if attempt >= MAX_ATTEMPTS:
                        sqs.send_message(QueueUrl=dlq, MessageBody=m["Body"])
                        sqs.delete_message(QueueUrl=q, ReceiptHandle=m["ReceiptHandle"])
                        log.error(f"GAVE UP on {key} after {attempt} attempts: event sent to {DLQ}")
                    else:
                        log.warning(f"will retry {key} in about {VISIBILITY} s")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
