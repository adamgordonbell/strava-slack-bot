.PHONY: config deploy send send-bad logs

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

send:
	uv run scripts/send_run.py $$(cd infra && pulumi stack output queue_url) $(TYPE)

# Simulate a bad Strava payload — triggers Lambda errors + DLQ for NR demo
send-bad:
	uv run scripts/send_run.py $$(cd infra && pulumi stack output queue_url) bad

logs:
	aws logs tail /aws/lambda/strava-slack-bot --region us-east-1 --follow
