"""HTTP trigger: drop a fake run onto the queue, or flush New Relic.

Exposed through a Lambda function URL so a guest can generate data with curl:

    curl -H "x-trigger-key: $KEY" "$URL?type=easy"    # easy | long | tempo | bad
    curl -H "x-trigger-key: $KEY" "$URL?type=flush"   # ship the last run's telemetry
"""
import json
import os

import boto3

from runs import RUNS, message_for

QUEUE_URL = os.environ["QUEUE_URL"]
TARGET_FUNCTION = os.environ["TARGET_FUNCTION"]
TRIGGER_KEY = os.environ["TRIGGER_KEY"]

sqs = boto3.client("sqs")
lam = boto3.client("lambda")


def _response(status, body):
    return {"statusCode": status, "headers": {"content-type": "application/json"},
            "body": json.dumps(body) + "\n"}


def handler(event, context):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    if headers.get("x-trigger-key") != TRIGGER_KEY:
        return _response(403, {"error": "bad or missing x-trigger-key header"})

    run_type = (event.get("queryStringParameters") or {}).get("type", "easy")
    if run_type == "flush":
        lam.invoke(FunctionName=TARGET_FUNCTION, InvocationType="Event", Payload=b"{}")
        return _response(200, {"flushed": TARGET_FUNCTION})
    if run_type not in RUNS and run_type != "bad":
        return _response(400, {"error": f"unknown type {run_type!r}",
                               "choose_from": sorted(RUNS) + ["bad", "flush"]})
    message = message_for(run_type)
    sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps(message))
    return _response(200, {"sent": run_type, "message": message})
