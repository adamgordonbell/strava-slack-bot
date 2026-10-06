#!/usr/bin/env python3
"""Ask New Relic what it has seen from the bot in the last hour — no browser needed.

Needs NEW_RELIC_USER_API_KEY (a User key, NRAK-...) and NEW_RELIC_ACCOUNT_ID in the env.
"""
import json
import os
import sys
import urllib.request

KEY = os.environ.get("NEW_RELIC_USER_API_KEY")
ACCOUNT = os.environ.get("NEW_RELIC_ACCOUNT_ID")
if not KEY or not ACCOUNT:
    sys.exit("Set NEW_RELIC_USER_API_KEY and NEW_RELIC_ACCOUNT_ID first")
SINCE = sys.argv[1] if len(sys.argv) > 1 else "1 hour ago"


def nrql(q: str):
    gql = "{ actor { account(id: %s) { nrql(query: %s) { results } } } }" % (ACCOUNT, json.dumps(q))
    req = urllib.request.Request(
        "https://api.newrelic.com/graphql",
        data=json.dumps({"query": gql}).encode(),
        headers={"API-Key": KEY, "Content-Type": "application/json"},
    )
    body = json.load(urllib.request.urlopen(req))
    if "errors" in body:
        sys.exit(f"NerdGraph error: {body['errors']}")
    return body["data"]["actor"]["account"]["nrql"]["results"]


def one(q: str, field: str):
    rows = nrql(q)
    return rows[0].get(field) if rows else None


print(f"New Relic account {ACCOUNT}, since {SINCE}")
# APM mode (NEW_RELIC_APM_LAMBDA_MODE) reports Transaction/TransactionError;
# the older serverless mode reports AwsLambdaInvocation/AwsLambdaInvocationError.
print(f"  Transactions (APM) : {one(f'SELECT count(*) FROM Transaction SINCE {SINCE}', 'count')}")
print(f"  Txn errors (APM)   : {one(f'SELECT count(*) FROM TransactionError SINCE {SINCE}', 'count')}")
for row in nrql(f"SELECT count(*) FROM TransactionError FACET error.class, error.message SINCE {SINCE}"):
    print(f"      {row['count']:>3} × {row['facet'][0]}: {row['facet'][1]}")
print(f"  Lambda invocations : {one(f'SELECT count(*) FROM AwsLambdaInvocation SINCE {SINCE}', 'count')}  (serverless mode)")
print(f"  Lambda errors      : {one(f'SELECT count(*) FROM AwsLambdaInvocationError SINCE {SINCE}', 'count')}")
for row in nrql(f"SELECT count(*) FROM AwsLambdaInvocationError FACET error.class, error.message SINCE {SINCE}"):
    print(f"      {row['count']:>3} × {row['facet'][0]}: {row['facet'][1]}")
print(f"  LLM completions    : {one(f'SELECT count(*) FROM LlmChatCompletionSummary SINCE {SINCE}', 'count')}"
      f"  (model {one(f'SELECT latest(request.model) FROM LlmChatCompletionSummary SINCE {SINCE}', 'latest.request.model')})")
print(f"  Log lines          : {one(f'SELECT count(*) FROM Log SINCE {SINCE}', 'count')}"
      f"  ({one(f'SELECT count(*) FROM Log WHERE message LIKE %KeyError% SINCE {SINCE}'.replace('%KeyError%', chr(39)+'%KeyError%'+chr(39)), 'count')} mention KeyError)")
