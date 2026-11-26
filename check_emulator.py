"""Check that the emulator is running and the services we use answer.

    python check_emulator.py
"""
import sys
import _aws

print(f"Endpoint: {_aws.endpoint()}")
ok = True
for service, call in [
    ("s3", lambda c: c.list_buckets()),
    ("dynamodb", lambda c: c.list_tables()),
    ("kinesis", lambda c: c.list_streams()),
    ("sqs", lambda c: c.list_queues()),
    ("cloudformation", lambda c: c.list_stacks()),
]:
    try:
        call(_aws.client(service))
        print(f"  OK    {service}")
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"  FAIL  {service}: {type(e).__name__}: {e}")

if ok:
    print("Emulator OK")
else:
    print("Is moto_server running in T1?  moto_server -p 9324")
    sys.exit(1)
