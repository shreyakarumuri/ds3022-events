"""Session 3: deploy or delete the CloudFormation stack in template.yaml.

    python s3_lambda/stack.py create
    python s3_lambda/stack.py status
    python s3_lambda/stack.py delete      # removes the bucket and both tables

The emulator keeps everything in memory: after restarting moto_server, run create again.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _aws  # noqa: E402

STACK = "ds3022-sensor-files"
TEMPLATE = Path(__file__).resolve().parent / "template.yaml"


def status(cf):
    try:
        s = cf.describe_stacks(StackName=STACK)["Stacks"][0]
    except cf.exceptions.ClientError:
        print(f"Stack {STACK} does not exist.")
        return
    print(f"Stack {STACK}: {s['StackStatus']}")
    for o in s.get("Outputs", []):
        print(f"  {o['OutputKey']:<14} {o['OutputValue']}")
    for r in cf.list_stack_resources(StackName=STACK)["StackResourceSummaries"]:
        print(f"  resource {r['LogicalResourceId']:<9} {r['ResourceType']:<26} {r['ResourceStatus']}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    cf = _aws.client("cloudformation")
    if cmd == "create":
        try:
            cf.create_stack(StackName=STACK, TemplateBody=TEMPLATE.read_text())
            cf.get_waiter("stack_create_complete").wait(StackName=STACK)
        except cf.exceptions.AlreadyExistsException:
            print(f"Stack {STACK} already exists (nothing to do).")
    elif cmd == "delete":
        s3 = _aws.resource("s3")
        for o in cf.describe_stacks(StackName=STACK)["Stacks"][0].get("Outputs", []):
            if o["OutputKey"] == "BucketName":
                s3.Bucket(o["OutputValue"]).objects.all().delete()  # a bucket must be empty to be deleted
        cf.delete_stack(StackName=STACK)
        cf.get_waiter("stack_delete_complete").wait(StackName=STACK)
        print(f"Deleted stack {STACK}.")
        return
    status(cf)


if __name__ == "__main__":
    main()
