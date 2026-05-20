# strava-slack-bot

Demo app for Pulumi × New Relic live stream.

Strava-shaped run events → SQS → Lambda (container) → Slack

## Structure

```
app/        Python Lambda handler
infra/      Pulumi program (coming)
scripts/    Local test helpers
Dockerfile
```

## Message shape

```json
{
  "activity": {
    "name": "Easy morning run",
    "activity_type": "Run",
    "distance_km": 8.3,
    "moving_time_min": 48,
    "pace_str": "5:47",
    "elevation_gain_m": 62,
    "avg_hr": 141.0
  }
}
```

## Local test

```bash
python scripts/send_run.py <sqs-queue-url>
```

## Config (env vars)

| Var | Description |
|-----|-------------|
| `SLACK_BOT_TOKEN` | Slack bot token (`xoxb-...`) — store in Pulumi ESC |
| `SLACK_CHANNEL` | Target channel (default: `#bot-testing`) |
