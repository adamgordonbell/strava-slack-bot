#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["boto3"]
# ///
"""Send a fake Strava run event to SQS for local testing.

Usage:
  send_run.py <queue-url> [easy|long|tempo|bad]

  bad: simulates a malformed payload (missing 'activity' wrapper) to
       trigger Lambda errors and demonstrate New Relic alerting + DLQ.
"""
import json
import os
import sys
import boto3

QUEUE_URL = sys.argv[1] if len(sys.argv) > 1 else None
RUN_TYPE = sys.argv[2] if len(sys.argv) > 2 else "easy"

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trigger"))
from runs import RUNS, message_for  # noqa: E402

if not QUEUE_URL:
    print("Usage: send_run.py <sqs-queue-url> [easy|long|tempo|bad]")
    sys.exit(1)

if RUN_TYPE in RUNS or RUN_TYPE == "bad":
    message = message_for(RUN_TYPE)
else:
    print(f"Unknown run type '{RUN_TYPE}'. Choose from: easy, long, tempo, bad")
    sys.exit(1)
sqs = boto3.client("sqs", region_name=os.environ.get("AWS_DEFAULT_REGION", "ca-central-1"))
sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps(message))
print(f"Sent [{RUN_TYPE}]:", json.dumps(message, indent=2))
