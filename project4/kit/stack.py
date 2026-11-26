"""Project 4: deploy or delete the CloudFormation stack in ../template.yaml. Do not edit.

    python kit/stack.py create
    python kit/stack.py status
    python kit/stack.py delete      # removes the bucket and every table in the template
    python kit/stack.py recreate    # delete + create: use it after you change the keys in template.yaml

The emulator keeps everything in memory: after restarting moto_server, run create again.
"""
import sys

import _aws
import _dp4

STACK = _dp4.STACK
TEMPLATE = _dp4.PROJECT / "template.yaml"


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
    elif cmd in ("delete", "recreate"):
        s3 = _aws.resource("s3")
        for o in cf.describe_stacks(StackName=STACK)["Stacks"][0].get("Outputs", []):
            if o["OutputKey"] == "BucketName":
                s3.Bucket(o["OutputValue"]).objects.all().delete()  # a bucket must be empty to be deleted
        cf.delete_stack(StackName=STACK)
        cf.get_waiter("stack_delete_complete").wait(StackName=STACK)
        print(f"Deleted stack {STACK}.")
        if cmd == "delete":
            return
        cf.create_stack(StackName=STACK, TemplateBody=TEMPLATE.read_text())
        cf.get_waiter("stack_create_complete").wait(StackName=STACK)
        print("Created it again. Restart kit/local_lambda.py: the bucket's trigger was deleted with the bucket.")
    status(cf)


if __name__ == "__main__":
    main()
