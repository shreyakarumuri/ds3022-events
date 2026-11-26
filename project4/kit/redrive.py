"""Project 4: move failed events from the dead-letter queue back to the event queue.

After you fix the bug that made them fail, redrive them: nothing was lost.

    python kit/redrive.py           # show what is waiting in the DLQ
    python kit/redrive.py --go      # send them back to be processed again
"""
import json
import sys
from urllib.parse import unquote_plus

import _aws
import _dp4

QUEUE, DLQ = _dp4.QUEUE, _dp4.DLQ


def main():
    go = "--go" in sys.argv
    sqs = _aws.client("sqs")
    q, dlq = (sqs.get_queue_url(QueueName=n)["QueueUrl"] for n in (QUEUE, DLQ))
    moved = 0
    while True:
        msgs = sqs.receive_message(QueueUrl=dlq, MaxNumberOfMessages=10, WaitTimeSeconds=1,
                                   VisibilityTimeout=0 if not go else 30).get("Messages", [])
        if not msgs:
            break
        for m in msgs:
            key = unquote_plus(json.loads(m["Body"])["Records"][0]["s3"]["object"]["key"])
            if go:
                sqs.send_message(QueueUrl=q, MessageBody=m["Body"])
                sqs.delete_message(QueueUrl=dlq, ReceiptHandle=m["ReceiptHandle"])
                moved += 1
                print(f"redriven: {key}")
            else:
                print(f"in DLQ: {key}")
        if not go:
            break
    n = sqs.get_queue_attributes(QueueUrl=dlq, AttributeNames=["ApproximateNumberOfMessages"])["Attributes"]
    print(f"Moved {moved}. Left in {DLQ}: {n['ApproximateNumberOfMessages']}" if go else "Run with --go to send them back.")


if __name__ == "__main__":
    main()
