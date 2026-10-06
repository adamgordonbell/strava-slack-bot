# Live stream walkthrough

Point-form build-out for the Pulumi × New Relic live stream (Oct 7).

> **TODO:** Add step-by-step section walking through *building* the Pulumi infrastructure
> from scratch — ECR repo, SQS + DLQ, IAM role, Lambda function, event source mapping.
> This is the main live-coding arc before the failure demo.

## 0. Prerequisites

- Pulumi CLI, uv, Docker, AWS credentials
- A Slack bot token in `.env` (see README)

## 1. Deploy

Secrets live in the Pulumi ESC environment `strava-slack-bot/dev`, which the stack imports.

```bash
cd infra
pulumi config            # stack config, with the ESC values merged in (secrets masked)
pulumi preview           # what would change
pulumi up                # build container → ECR → Lambda + SQS + DLQ
pulumi stack output      # queue URL, DLQ URL, trigger URL
cd ..
```

`make` targets below are helper scripts for sending test events; everything Pulumi does is
shown as the plain `pulumi` command.

## 2. Send a run

```bash
make send TYPE=easy    # easy morning run
make send TYPE=tempo   # tempo Tuesday
make send TYPE=long    # Sunday long run
```

Watch Slack — PulumiBot posts run stats + AI coaching feedback.

## 3. Trigger the failure

```bash
make flood-bad
```

Sends 5 malformed payloads. Each hits the Lambda 3× before landing in the DLQ → **15 Lambda errors** visible in New Relic.

## 4. Observe in New Relic

- Lambda error rate spikes
- Stack traces show `KeyError: 'activity'`
- DLQ depth climbs to 5

## 5. Fix the handler

In `app/handler.py`, add a guard before `body["activity"]`:

```python
if "activity" not in body:
    print(f"Skipping malformed message: {body}")
    continue
```

## 6. Redeploy + redrive

```bash
cd infra && pulumi up && cd ..   # preview shows the image + Lambda changing; confirm
make redrive                     # move DLQ messages back to main queue
make logs                        # watch them succeed (Ctrl-C to stop)
```

New Relic error rate returns to zero. DLQ drains.
