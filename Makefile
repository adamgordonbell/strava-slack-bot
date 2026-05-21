.PHONY: deploy send logs

deploy:
	cd infra && pulumi up

send:
	uv run scripts/send_run.py $$(cd infra && pulumi stack output queue_url)

logs:
	aws logs tail /aws/lambda/strava-slack-bot --region us-east-1 --follow
