#!/usr/bin/env python3
"""Send a fake Strava run event to SQS for local testing."""
import json
import sys
import boto3

QUEUE_URL = sys.argv[1] if len(sys.argv) > 1 else None

SAMPLE_RUN = {
    "activity": {
        "name": "Easy morning run",
        "activity_type": "Run",
        "distance_km": 8.3,
        "moving_time_min": 48,
        "pace_str": "5:47",
        "elevation_gain_m": 62,
        "avg_hr": 141.0,
    }
}

if not QUEUE_URL:
    print("Usage: send_run.py <sqs-queue-url>")
    sys.exit(1)

sqs = boto3.client("sqs")
sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps(SAMPLE_RUN))
print("Sent:", json.dumps(SAMPLE_RUN, indent=2))
