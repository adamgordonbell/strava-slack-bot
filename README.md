# strava-slack-bot

Demo app for the Pulumi × New Relic live stream.

Strava-shaped run events arrive on an SQS queue, a Lambda function processes them and posts a summary to Slack. Pulumi manages all the infrastructure. New Relic instruments the Lambda.

```
SQS queue → Lambda (container on ECR) → Slack
```

## Prerequisites

- [Pulumi CLI](https://www.pulumi.com/docs/install/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (for the test script)
- AWS credentials configured
- Docker (for building the container image)
- A Slack bot token (`xoxb-...`) and a channel to post to

## Structure

```
app/        Python Lambda handler
infra/      Pulumi program (Python)
scripts/    Local test helpers
Dockerfile
Makefile
```

## Deploy

```bash
cd infra
pip install -r requirements.txt   # first time only
```

### Option A — Pulumi ESC (recommended)

Create an ESC environment and set your secrets there:

```bash
esc env init <your-org>/strava-slack-bot/dev
esc env set --secret <your-org>/strava-slack-bot/dev pulumiConfig.strava-slack-bot:slackBotToken xoxb-...
esc env set <your-org>/strava-slack-bot/dev pulumiConfig.strava-slack-bot:slackChannel my-channel
```

Then reference it in `infra/Pulumi.dev.yaml`:

```yaml
environment:
  - strava-slack-bot/dev
config:
  aws:region: us-east-1
```

### Option B — plain config

```bash
cd infra
pulumi config set slackChannel my-channel
pulumi config set --secret slackBotToken xoxb-...
```

### Run

```bash
make deploy
```

Pulumi builds the Docker image, pushes it to ECR, and provisions everything (ECR repo, SQS queue + DLQ, IAM role, Lambda, event source mapping).

## Test

Send a fake Strava run to the queue:

```bash
make send
```

Watch the Lambda logs:

```bash
make logs
```

## SQS message shape

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

## Config reference

| Key | Description |
|-----|-------------|
| `slackBotToken` | Slack bot token (`xoxb-...`) — keep secret |
| `slackChannel` | Channel name to post to (without `#`) |
| `aws:region` | AWS region (default `us-east-1`) |
