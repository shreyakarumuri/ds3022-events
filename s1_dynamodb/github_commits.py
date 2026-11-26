"""Session 1: JSON from a REST API into DynamoDB, and why the key design matters.

Adapted from Neal's learn-dynamodb/hands-on/advanced (inspect-commits.py,
load-commits.py) and the "JSON Serialization and Deserialization with REST
APIs" lab (missing fields, error handling, saving JSON to a file).

Two designs for the same access pattern "the 10 most recent commits of a repo":
  design a (Neal's):  partition key repo,  sort key sha
  design b:           partition key repo,  sort key committed_at#sha

Usage (from the repo root):
    python s1_dynamodb/github_commits.py fetch boto/boto3          # 1 API request, saved to data/
    python s1_dynamodb/github_commits.py fetch boto/boto3 --offline  # use the sample file instead
    python s1_dynamodb/github_commits.py load data/commits_boto_boto3.json
    python s1_dynamodb/github_commits.py latest boto/boto3 --design a
    python s1_dynamodb/github_commits.py latest boto/boto3 --design b

GitHub allows 60 unauthenticated requests per hour per IP address, and the whole
classroom shares one IP. fetch makes ONE request and saves the result; everything
else reads the saved file. If fetch reports the rate limit, use --offline.
"""
import argparse
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _aws  # noqa: E402

from boto3.dynamodb.conditions import Key  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
SAMPLE = DATA / "sample_commits_boto3_boto3.json"
TABLES = {"a": ("commits_a", "sha"), "b": ("commits_b", "sk")}


# ---------- 1. Fetch: REST + JSON deserialisation + error handling ----------

def fetch(args):
    owner_repo = args.repo
    out = DATA / f"commits_{owner_repo.replace('/', '_')}.json"
    DATA.mkdir(exist_ok=True)
    if args.offline:
        if owner_repo != "boto/boto3":
            sys.exit("The offline sample only exists for boto/boto3.")
        data = json.loads(SAMPLE.read_text(encoding="utf-8"))
        print(f"Offline: using the saved file {SAMPLE.name} ({len(data)} commits).")
    else:
        url = f"https://api.github.com/repos/{owner_repo}/commits"
        try:
            r = requests.get(url, params={"per_page": 100},
                             headers={"Accept": "application/vnd.github+json"}, timeout=10)
        except requests.RequestException as e:
            sys.exit(f"Network error: {e}. Try again, or use --offline.")
        remaining = r.headers.get("X-RateLimit-Remaining")
        if r.status_code in (403, 429) and remaining == "0":
            sys.exit(f"Rate limited (60 requests/hour per IP). Resets at epoch {r.headers.get('X-RateLimit-Reset')}. Use --offline.")
        if r.status_code == 404:
            sys.exit(f"404: {owner_repo} does not exist or is private.")
        r.raise_for_status()
        try:
            data = r.json()  # deserialise: JSON text -> Python list of dicts
        except ValueError:
            sys.exit("The response was not valid JSON.")
        print(f"Fetched {len(data)} commits. Requests left this hour from this IP: {remaining}")
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")  # serialise back to a file
    print(f"Saved to {out.relative_to(DATA.parent)}")
    for c in data[:5]:
        print("  " + summary(c, owner_repo)["line"])


def summary(c, repo):
    """Flatten one commit. Nested fields can be missing or null: never index blindly."""
    commit = c.get("commit") or {}
    author = commit.get("author") or {}
    login = (c.get("author") or {}).get("login", "(no GitHub account)")  # top-level author can be null
    message = (commit.get("message") or "").splitlines()
    item = {
        "repo": repo,
        "sha": c["sha"],
        "author_name": author.get("name", "unknown"),
        "author_login": login,
        "committed_at": author.get("date", "1970-01-01T00:00:00Z"),
        "message": message[0] if message else "",
        "url": c.get("html_url", ""),
    }
    item["sk"] = f"{item['committed_at']}#{item['sha'][:7]}"
    item["line"] = f"{item['sha'][:7]}  {item['committed_at']}  {item['author_name'][:20]:<20}  {item['message'][:50]}"
    return item


# ---------- 2. Load into two tables with different sort keys ----------

def ensure_table(name, sort_key):
    ddb = _aws.client("dynamodb")
    try:
        ddb.create_table(
            TableName=name,
            AttributeDefinitions=[{"AttributeName": "repo", "AttributeType": "S"},
                                  {"AttributeName": sort_key, "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "repo", "KeyType": "HASH"},
                       {"AttributeName": sort_key, "KeyType": "RANGE"}],
            BillingMode="PAY_PER_REQUEST",
        )
        ddb.get_waiter("table_exists").wait(TableName=name)
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceInUseException":
            raise


def load(args):
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    # each commit's API url looks like https://api.github.com/repos/<owner>/<repo>/commits/<sha>
    repo = args.repo or data[0]["url"].split("/repos/")[1].split("/commits/")[0]
    for design, (name, sort_key) in TABLES.items():
        ensure_table(name, sort_key)
        with _aws.resource("dynamodb").Table(name).batch_writer() as bw:
            for c in data:
                item = summary(c, repo)
                item.pop("line")
                if design == "a":
                    item.pop("sk")
                bw.put_item(Item=item)
        print(f"design {design}: {len(data)} commits loaded into {name} (sort key: {sort_key})")


# ---------- 3. The access pattern ----------

def latest(args):
    name, sort_key = TABLES[args.design]
    resp = _aws.resource("dynamodb").Table(name).query(
        KeyConditionExpression=Key("repo").eq(args.repo),
        ScanIndexForward=False,  # highest sort key first
        Limit=args.n,
    )
    print(f"design {args.design}: Query newest-first by {sort_key}")
    for it in resp["Items"]:
        print(f"  {it['sha'][:7]}  {it['committed_at']}  {it['message'][:50]}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("fetch"); s.add_argument("repo"); s.add_argument("--offline", action="store_true")
    s.set_defaults(fn=fetch)
    s = sub.add_parser("load"); s.add_argument("file"); s.add_argument("--repo"); s.set_defaults(fn=load)
    s = sub.add_parser("latest"); s.add_argument("repo"); s.add_argument("--design", choices="ab", default="b")
    s.add_argument("-n", type=int, default=10); s.set_defaults(fn=latest)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
