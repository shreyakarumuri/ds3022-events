"""Shared helper for the Project 4 kit scripts (same as ds3022-events/_aws.py).

Loads .env (if python-dotenv is installed) and makes sure boto3 talks to the
local emulator unless you say otherwise. Every script calls boto3 exactly as
it would on real AWS: the endpoint is the only difference.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # the .env of ds3022-events
except ImportError:
    pass

os.environ.setdefault("AWS_ENDPOINT_URL", "http://127.0.0.1:9324")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

import boto3  # noqa: E402  (import after the environment is set)


def client(service):
    return boto3.client(service)


def resource(service):
    return boto3.resource(service)


def endpoint():
    return os.environ.get("AWS_ENDPOINT_URL", "(real AWS)")
