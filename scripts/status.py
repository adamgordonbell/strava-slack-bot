#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["boto3"]
# ///
"""The poor man's dashboard: queue depths and recent Lambda activity from AWS alone.

Usage: status.py <queue-url> <dlq-url> [minutes] [--watch]
"""
import os
import re
import sys
import time
from datetime import datetime

import boto3

args = [a for a in sys.argv[1:] if not a.startswith("--")]
WATCH = "--watch" in sys.argv
QUEUE_URL, DLQ_URL = args[0], args[1]
MINUTES = int(args[2]) if len(args) > 2 else 15
REGION = os.environ.get("AWS_REGION", "ca-central-1")
LOG_GROUP = "/aws/lambda/strava-slack-bot"

sqs = boto3.client("sqs", region_name=REGION)
logs = boto3.client("logs", region_name=REGION)


def depth(url):
    a = sqs.get_queue_attributes(
        QueueUrl=url,
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )["Attributes"]
    return int(a["ApproximateNumberOfMessages"]), int(a["ApproximateNumberOfMessagesNotVisible"])


def events(pattern, since_ms):
    out, token = [], None
    while True:
        kw = dict(logGroupName=LOG_GROUP, startTime=since_ms, filterPattern=pattern)
        if token:
            kw["nextToken"] = token
        r = logs.filter_log_events(**kw)
        out += r["events"]
        token = r.get("nextToken")
        if not token:
            return out


def snapshot():
    since = int((time.time() - MINUTES * 60) * 1000)
    waiting, in_flight = depth(QUEUE_URL)
    dlq, _ = depth(DLQ_URL)
    reports = events("REPORT", since)
    errors = events('"[ERROR]"', since)
    skipped = events('"Skipping malformed"', since)
    durations = [float(m.group(1)) for e in reports
                 if (m := re.search(r"\tDuration: ([\d.]+) ms", e["message"]))]

    print(f"strava-slack-bot · {datetime.now():%H:%M:%S} · last {MINUTES} min")
    print(f"  queue      : {waiting} waiting, {in_flight} in flight")
    print(f"  DLQ        : {dlq}" + ("   <-- messages are dying here" if dlq else ""))
    print(f"  invocations: {len(reports)}")
    print(f"  errors     : {len(errors)}")
    if skipped:
        print(f"  skipped    : {len(skipped)} malformed (guard is in)")
    if durations:
        print(f"  duration   : avg {sum(durations)/len(durations):.0f} ms, max {max(durations):.0f} ms")
    for e in errors[-3:]:
        when = datetime.fromtimestamp(e["timestamp"] / 1000)
        line = e["message"].split("Traceback")[0].replace("\t", " ").strip()
        print(f"    {when:%H:%M:%S}  {line[:90]}")


if WATCH:
    while True:
        os.system("clear")
        snapshot()
        print("\n(Ctrl-C to stop)")
        time.sleep(5)
else:
    snapshot()
