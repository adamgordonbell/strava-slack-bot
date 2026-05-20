import json
import os
import urllib.request

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#bot-testing")


def format_run(activity: dict) -> str:
    name = activity.get("name", "Morning Run")
    distance = activity.get("distance_km", 0)
    duration = activity.get("moving_time_min", 0)
    pace_str = activity.get("pace_str", "")
    elevation = activity.get("elevation_gain_m", 0)

    lines = [f"🏃 *{name}*"]
    lines.append(f"{distance:.1f} km · {duration} min" + (f" · {pace_str}/km" if pace_str else ""))
    if elevation:
        lines.append(f"↑ {elevation:.0f} m elevation")

    avg_hr = activity.get("avg_hr")
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
        text = format_run(activity)
        post_to_slack(text)
    return {"statusCode": 200}
