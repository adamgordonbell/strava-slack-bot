.PHONY: config deploy send send-bad flood-bad redrive logs

QUEUE_URL = $(shell cd infra && pulumi stack output queue_url)
DLQ_ARN   = $(shell cd infra && pulumi stack output dlq_url | sed 's|https://sqs.\([^.]*\).amazonaws.com/\([^/]*\)/\(.*\)|arn:aws:sqs:\1:\2:\3|')
QUEUE_ARN = $(shell cd infra && pulumi stack output queue_url | sed 's|https://sqs.\([^.]*\).amazonaws.com/\([^/]*\)/\(.*\)|arn:aws:sqs:\1:\2:\3|')

# Read .env and push values into Pulumi config (run once, or when token changes)
config:
	@test -f .env || (echo "Copy .env.sample to .env and fill in your values first"; exit 1)
	@export $$(cat .env | xargs) && \
		cd infra && \
		pulumi config set --secret slackBotToken "$$SLACK_BOT_TOKEN" && \
		pulumi config set slackChannel "$$SLACK_CHANNEL" && \
		pulumi config set --secret anthropicApiKey "$$ANTHROPIC_API_KEY"
	@echo "Config set. Run 'make deploy' to deploy."

deploy:
	cd infra && pulumi up

# Send a single run event (TYPE=easy|long|tempo, default easy)
send:
	uv run scripts/send_run.py $(QUEUE_URL) $(TYPE)

# Send one bad payload — triggers Lambda error + eventual DLQ
send-bad:
	uv run scripts/send_run.py $(QUEUE_URL) bad

# Flood queue with bad payloads — triggers NR error spike + fills DLQ
flood-bad:
	@for i in 1 2 3 4 5; do \
		uv run scripts/send_run.py $(QUEUE_URL) bad 2>&1 | grep "Sent"; \
	done

# Move DLQ messages back to main queue after deploying a fix
redrive:
	aws sqs start-message-move-task \
		--source-arn $(DLQ_ARN) \
		--destination-arn $(QUEUE_ARN) \
		--region us-east-1
	@echo "Redrive started — messages will re-process shortly."

logs:
	aws logs tail /aws/lambda/strava-slack-bot --region us-east-1 --follow
