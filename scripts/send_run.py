#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["boto3"]
# ///
"""Send a fake Strava run event to SQS for local testing.

Usage:
  send_run.py <queue-url> [easy|long|tempo]
"""
import json
import sys
import boto3

QUEUE_URL = sys.argv[1] if len(sys.argv) > 1 else None
RUN_TYPE = sys.argv[2] if len(sys.argv) > 2 else "easy"

RUNS = {
    "easy": {
        "name": "Easy morning run",
        "activity_type": "Run",
        "run_type": "easy",
        "distance_km": 8.3,
        "moving_time_min": 48,
        "pace_str": "5:47",
        "elevation_gain_m": 42,
        "avg_hr": 138.0,
        "hr_zones": {"1": 5, "2": 78, "3": 15, "4": 2, "5": 0},
        "splits": ["5:51", "5:49", "5:45", "5:44", "5:48", "5:50", "5:47", "5:43"],
    },
    "long": {
        "name": "Sunday long run",
        "activity_type": "Run",
        "run_type": "long",
        "distance_km": 18.5,
        "moving_time_min": 112,
        "pace_str": "6:03",
        "elevation_gain_m": 145,
        "avg_hr": 148.0,
        "hr_zones": {"1": 2, "2": 55, "3": 35, "4": 8, "5": 0},
        "splits": ["6:10", "6:05", "6:02", "5:58", "6:00", "6:04", "6:08", "6:12",
                   "6:15", "6:10", "6:05", "6:02", "6:08", "6:14", "6:18", "6:20",
                   "6:22", "5:58"],
    },
    "tempo": {
        "name": "Tempo Tuesday",
        "activity_type": "Run",
        "run_type": "tempo",
        "distance_km": 6.2,
        "moving_time_min": 28,
        "pace_str": "4:31",
        "elevation_gain_m": 18,
        "avg_hr": 171.0,
        "hr_zones": {"1": 0, "2": 5, "3": 18, "4": 62, "5": 15},
        "splits": ["4:42", "4:35", "4:29", "4:28", "4:27", "4:26"],
    },
}

if not QUEUE_URL:
    print("Usage: send_run.py <sqs-queue-url> [easy|long|tempo]")
    sys.exit(1)

if RUN_TYPE not in RUNS:
    print(f"Unknown run type '{RUN_TYPE}'. Choose from: {', '.join(RUNS)}")
    sys.exit(1)

message = {"activity": RUNS[RUN_TYPE]}
sqs = boto3.client("sqs", region_name="us-east-1")
sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps(message))
print(f"Sent [{RUN_TYPE}]:", json.dumps(message, indent=2))
