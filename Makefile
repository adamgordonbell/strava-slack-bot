.PHONY: config deploy send send-bad flood-bad flush trigger trigger-url redrive logs nr-check

REGION    ?= ca-central-1
QUEUE_URL  = $(shell cd infra && pulumi stack output queue_url)
TRIGGER_URL = $(shell cd infra && pulumi stack output trigger_url)
TRIGGER_KEY = $(shell cd infra && pulumi config get triggerKey)
DLQ_ARN    = $(shell cd infra && pulumi stack output dlq_url | sed 's|https://sqs.\([^.]*\).amazonaws.com/\([^/]*\)/\(.*\)|arn:aws:sqs:\1:\2:\3|')
QUEUE_ARN  = $(shell cd infra && pulumi stack output queue_url | sed 's|https://sqs.\([^.]*\).amazonaws.com/\([^/]*\)/\(.*\)|arn:aws:sqs:\1:\2:\3|')

# Read .env and push values into Pulumi config (run once, or when token changes)
config:
	@test -f .env || (echo "Copy .env.sample to .env and fill in your values first"; exit 1)
	@export $$(cat .env | xargs) && \
		cd infra && \
		pulumi config set --secret slackBotToken "$$SLACK_BOT_TOKEN" && \
		pulumi config set slackChannel "$$SLACK_CHANNEL" && \
		if [ -n "$$NEW_RELIC_LICENSE_KEY" ]; then \
			pulumi config set --secret newRelicLicenseKey "$$NEW_RELIC_LICENSE_KEY" && \
			pulumi config set newRelicAccountId "$$NEW_RELIC_ACCOUNT_ID"; \
		fi
	@echo "Config set. Run 'make deploy' to deploy."

deploy:
	cd infra && pulumi up --yes

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
		--region $(REGION)
	@echo "Redrive started — messages will re-process shortly."

logs:
	aws logs tail /aws/lambda/strava-slack-bot --region $(REGION) --follow

# Same as `make send` / `make flush`, but over HTTP through the trigger function
# URL (TYPE=easy|long|tempo|bad|flush). This is what a guest without AWS access uses.
trigger:
	@curl -s -H "x-trigger-key: $(TRIGGER_KEY)" "$(TRIGGER_URL)?type=$(TYPE)"

# Print the curl line to hand to a guest (includes the key: share privately).
trigger-url:
	@echo 'curl -H "x-trigger-key: $(TRIGGER_KEY)" "$(TRIGGER_URL)?type=easy"   # easy | long | tempo | bad | flush'

# Push the last invocation's telemetry to New Relic. In APM mode the extension
# only sends a payload when the *next* invocation starts (or at shutdown), so a
# lone `make send` is invisible until something else runs. This is that something.
flush:
	@aws lambda invoke --region $(REGION) --function-name strava-slack-bot \
		--invocation-type Event --payload '{}' /dev/null >/dev/null && echo "Flushed"

# What New Relic has seen in the last hour (needs NEW_RELIC_USER_API_KEY + NEW_RELIC_ACCOUNT_ID)
nr-check:
	python3 scripts/nr_check.py "$${SINCE:-1 hour ago}"
