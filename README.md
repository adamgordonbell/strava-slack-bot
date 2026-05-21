# strava-slack-bot

![PulumiBot posting coaching feedback to Slack](docs/slack-demo.png)

Get AI coaching feedback on every run, posted to Slack automatically. Each run syncs from Strava via a webhook bridge into SQS, a Lambda function calls Claude to generate a short coaching note, and the result lands in a channel of your choice. Pulumi manages the infrastructure; New Relic instruments it for observability.

```
Strava → [webhook bridge] → SQS → Lambda (container) → Slack
```

> **Note:** This is the live-stream version — designed to be deployed and broken on camera.
> For a more complete implementation from the "I Built an AI Running Coach" talk, see
> [adamgordonbell/ai-running-coach](https://github.com/adamgordonbell/ai-running-coach).

## Prerequisites

- [Pulumi CLI](https://www.pulumi.com/docs/install/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- AWS credentials configured
- Docker
- A Slack bot token — see [Setting up the Slack bot](#setting-up-the-slack-bot)

## Quickstart

```bash
cp .env.sample .env
# fill in SLACK_BOT_TOKEN, SLACK_CHANNEL, and ANTHROPIC_API_KEY in .env

make config    # pushes .env values into Pulumi config
make deploy    # builds container, pushes to ECR, provisions everything
make send      # sends a test run event (TYPE=easy|long|tempo, default easy)
make logs      # tail Lambda logs
```

## Setting up the Slack bot

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → From scratch
2. Under **OAuth & Permissions**, add these bot token scopes:
   - `chat:write`, `chat:write.public`
3. Click **Install to Workspace** — copy the **Bot User OAuth Token** (`xoxb-...`)
4. Invite the bot to your channel: `/invite @your-bot-name`

Put the token in `.env` as `SLACK_BOT_TOKEN`.

## What gets deployed

- **ECR** — container image repository
- **SQS queue** — receives run events (with a dead-letter queue)
- **Lambda** — processes events and posts to Slack
- **IAM** — role with least-privilege SQS access

## SQS message shape

```json
{
  "activity": {
    "name": "Easy morning run",
    "activity_type": "Run",
    "run_type": "easy",
    "distance_km": 8.3,
    "moving_time_min": 48,
    "pace_str": "5:47",
    "elevation_gain_m": 42,
    "avg_hr": 138.0,
    "hr_zones": {"1": 5, "2": 78, "3": 15, "4": 2, "5": 0},
    "splits": ["5:51", "5:49", "5:45", "5:44", "5:48", "5:50", "5:47", "5:43"]
  }
}
```

## Using Pulumi ESC instead of .env

If you prefer to manage secrets in [Pulumi ESC](https://www.pulumi.com/docs/esc/), skip `make config` and set up an ESC environment instead:

```bash
esc env init <your-org>/strava-slack-bot/dev
esc env set --secret <your-org>/strava-slack-bot/dev pulumiConfig.strava-slack-bot:slackBotToken xoxb-...
esc env set <your-org>/strava-slack-bot/dev pulumiConfig.strava-slack-bot:slackChannel your-channel
esc env set --secret <your-org>/strava-slack-bot/dev pulumiConfig.strava-slack-bot:anthropicApiKey sk-ant-...
```

Then reference it in `infra/Pulumi.dev.yaml`:

```yaml
environment:
  - strava-slack-bot/dev
config:
  aws:region: us-east-1
```

## Setting up a Strava-to-SQS bridge

This demo uses synthetic run events (`make send`), but to wire in real Strava data:

1. Create a [Strava API application](https://developers.strava.com/docs/getting-started/) and subscribe to the webhook.
2. Deploy a small HTTP endpoint (API Gateway + Lambda or a simple server) that receives the Strava webhook POST and forwards it to SQS.
3. Point the webhook subscription at that endpoint.

The SQS message format is documented in [SQS message shape](#sqs-message-shape).

## Going further

- **Move to Fargate** — swap the Lambda for an ECS Fargate task to handle longer-running workloads and persistent connections.
- **Try Google Cloud Run** — port the Pulumi program to GCP using `pulumi-gcp`; the container and app code stay the same.
- **Wire a real Strava bridge** — set up the webhook integration above so your actual runs trigger the bot automatically.
- **Add a New Relic custom dashboard** — instrument the Lambda to emit a custom metric (run distance, coaching latency) and track your training over time.

For the live-stream failure scenario and step-by-step walkthrough, see [TUTORIAL.md](TUTORIAL.md).

---

*This repo is used live in the [Pulumi × New Relic live stream](https://www.pulumi.com). Adam posts to `#test-pulumi-bot` in the [Pulumi Community Slack](https://slack.pulumi.com).*
