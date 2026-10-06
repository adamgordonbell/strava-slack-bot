import json
import os
import urllib.request

import boto3

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "bot-testing")
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
)
BEDROCK_REGION = os.environ.get("BEDROCK_REGION") or os.environ.get("AWS_REGION", "ca-central-1")

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def coaching_feedback(activity: dict) -> str:
    run_type = activity.get("run_type", "run")
    distance = activity.get("distance_km", 0)
    duration = activity.get("moving_time_min", 0)
    pace_str = activity.get("pace_str", "")
    hr_zones = activity.get("hr_zones", {})
    splits = activity.get("splits", [])

    zones_text = ""
    if hr_zones:
        zones_text = "HR zones (% time): " + ", ".join(
            f"Z{z}={hr_zones[z]}%" for z in sorted(hr_zones)
        )

    splits_text = ""
    if splits:
        splits_text = "Splits (pace/km): " + ", ".join(
            f"km{i+1} {s}" for i, s in enumerate(splits)
        )

    prompt = f"""You are a supportive running coach giving brief post-run feedback.
Be specific to the numbers, encouraging but honest. 2-3 sentences max.

Run: {run_type}, {distance}km in {duration} min ({pace_str}/km avg)
{zones_text}
{splits_text}

Give brief coaching feedback."""

    # Claude on Amazon Bedrock via the Converse API. New Relic's Python agent
    # instruments this call, so it shows up as an LLM trace (AI monitoring).
    resp = bedrock.converse(
        modelId=BEDROCK_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 150},
    )
    return resp["output"]["message"]["content"][0]["text"].strip()


def format_header(activity: dict) -> str:
    name = activity.get("name", "Run")
    distance = activity.get("distance_km", 0)
    duration = activity.get("moving_time_min", 0)
    pace_str = activity.get("pace_str", "")
    elevation = activity.get("elevation_gain_m", 0)
    avg_hr = activity.get("avg_hr")

    lines = [f"🏃 *{name}*"]
    lines.append(f"{distance:.1f} km · {duration} min" + (f" · {pace_str}/km" if pace_str else ""))
    if elevation:
        lines.append(f"↑ {elevation:.0f} m elevation")
    if avg_hr:
        lines.append(f"❤️ avg HR {avg_hr:.0f} bpm")
    return "\n".join(lines)


def post_to_slack(text: str) -> None:
    payload = json.dumps({"channel": SLACK_CHANNEL, "text": text}).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
        if not body.get("ok"):
            raise RuntimeError(f"Slack error: {body.get('error')}")


def handler(event, context):
    if "Records" not in event:
        # `make flush`: an empty direct invoke. New Relic's extension only ships
        # the previous invocation's telemetry when the next one starts, so this
        # nudges it out. Keep the ping itself out of New Relic.
        try:
            import newrelic.agent
            newrelic.agent.ignore_transaction()
        except ImportError:
            pass
        return {"statusCode": 204}
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        activity = body["activity"]
        header = format_header(activity)
        feedback = coaching_feedback(activity)
        post_to_slack(f"{header}\n\n_{feedback}_")
    return {"statusCode": 200}
