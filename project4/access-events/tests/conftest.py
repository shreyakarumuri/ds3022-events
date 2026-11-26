"""Shared test setup: an in-process fake AWS (moto), the two tables and the bucket.
Table keys are read from ../template.yaml, so the tests follow your key design."""
import os
import sys
from pathlib import Path

import boto3
import pytest
import yaml
from moto import mock_aws

APP_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = APP_DIR.parent / "template.yaml"
BUCKET = "test-bucket"

sys.path.insert(0, str(APP_DIR))
os.environ.update({"APP_BUCKET_NAME": BUCKET, "ACCESS_TABLE": "access", "FILELOG_TABLE": "file_log",
                   "AWS_DEFAULT_REGION": "us-east-1", "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"})


class _Loader(yaml.SafeLoader):
    pass


# CloudFormation tags such as !Ref and !Sub: keep their value, ignore the tag
_Loader.add_multi_constructor("!", lambda loader, suffix, node: loader.construct_scalar(node)
                              if isinstance(node, yaml.ScalarNode) else loader.construct_sequence(node))


def tables_from_template():
    doc = yaml.load(TEMPLATE.read_text(), Loader=_Loader)
    for res in doc["Resources"].values():
        if res["Type"] == "AWS::DynamoDB::Table":
            p = dict(res["Properties"])
            p.pop("StreamSpecification", None)
            yield p


@pytest.fixture
def aws(monkeypatch):
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)  # never send test traffic to the running emulator
    with mock_aws():
        boto3.client("s3").create_bucket(Bucket=BUCKET)
        ddb = boto3.client("dynamodb")
        for props in tables_from_template():
            ddb.create_table(**props)
        import app as app_module  # import inside the fake so its boto3 clients are faked too
        yield app_module
