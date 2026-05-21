import json
import os
import urllib.request

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "bot-testing")
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]


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

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 150,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
        return body["content"][0]["text"].strip()


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
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        activity = body["activity"]
        header = format_header(activity)
        feedback = coaching_feedback(activity)
        post_to_slack(f"{header}\n\n_{feedback}_")
    return {"statusCode": 200}
