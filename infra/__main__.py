import json
import pulumi
import pulumi_aws as aws
import pulumi_docker as docker

config = pulumi.Config()
slack_bot_token = config.require_secret("slackBotToken")
slack_channel = config.get("slackChannel") or "bot-testing"
bedrock_model_id = config.get("bedrockModelId") or "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# New Relic is optional: leave newRelicLicenseKey unset and the function runs
# un-instrumented. Set it (plus newRelicAccountId) and the Lambda boots through
# New Relic's handler wrapper with AI monitoring on.
new_relic_license_key = config.get_secret("newRelicLicenseKey")
new_relic_account_id = config.get("newRelicAccountId")
new_relic_enabled = new_relic_license_key is not None
# `pulumi config set newRelicDebug true` for verbose extension + agent logs in CloudWatch.
new_relic_debug = config.get_bool("newRelicDebug") or False

# ECR repo
repo = aws.ecr.Repository(
    "strava-slack-bot",
    name="strava-slack-bot",
    image_tag_mutability="MUTABLE",
    force_delete=True,
)

# Auth token for pushing to ECR
auth_token = aws.ecr.get_authorization_token_output(registry_id=repo.registry_id)

# Build and push the container image
image = docker.Image(
    "strava-slack-bot-image",
    build=docker.DockerBuildArgs(
        context="..",
        dockerfile="../Dockerfile",
        platform="linux/arm64",
    ),
    image_name=repo.repository_url.apply(lambda url: f"{url}:latest"),
    registry=docker.RegistryArgs(
        server=repo.repository_url,
        username=auth_token.user_name,
        password=auth_token.password,
    ),
)

# SQS dead-letter queue
dlq = aws.sqs.Queue(
    "strava-slack-bot-dlq",
    name="strava-slack-bot-dlq",
    message_retention_seconds=1209600,  # 14 days
)

# SQS queue — run events land here
queue = aws.sqs.Queue(
    "strava-slack-bot-queue",
    name="strava-slack-bot",
    visibility_timeout_seconds=60,
    redrive_policy=pulumi.Output.json_dumps({
        "deadLetterTargetArn": dlq.arn,
        "maxReceiveCount": 3,
    }),
)

# IAM role for Lambda
lambda_role = aws.iam.Role(
    "strava-slack-bot-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Effect": "Allow",
        }],
    }),
)

aws.iam.RolePolicyAttachment(
    "basic-execution",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
)

aws.iam.RolePolicy(
    "sqs-read-policy",
    role=lambda_role.name,
    policy=pulumi.Output.json_dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes",
            ],
            "Resource": [queue.arn, dlq.arn],
        }],
    }),
)

# Claude on Bedrock. The cross-region inference profile can route to any US
# region, so the resource has to stay open.
aws.iam.RolePolicy(
    "bedrock-invoke-policy",
    role=lambda_role.name,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            "Resource": "*",
        }],
    }),
)

env_vars = {
    "SLACK_BOT_TOKEN": slack_bot_token,
    "SLACK_CHANNEL": slack_channel,
    "BEDROCK_MODEL_ID": bedrock_model_id,
}
image_command = None
if new_relic_enabled:
    env_vars.update({
        "NEW_RELIC_LICENSE_KEY": new_relic_license_key,
        "NEW_RELIC_ACCOUNT_ID": new_relic_account_id or "",
        # The wrapper imports this to find the real handler.
        "NEW_RELIC_LAMBDA_HANDLER": "handler.handler",
        # LLM traces for the Bedrock converse call (off by default in the agent).
        "NEW_RELIC_AI_MONITORING_ENABLED": "true",
        # Ship function logs (the KeyError traceback) through the extension.
        "NEW_RELIC_EXTENSION_SEND_FUNCTION_LOGS": "true",
        # Ship each invocation's telemetry at the end of that invocation. By
        # default the extension batches agent payloads (3 per send) and holds
        # the rest until the container's next invocation or shutdown, which
        # makes a single `make send` invisible in New Relic for minutes.
        "NEW_RELIC_EXTENSION_SYNCHRONOUS_FLUSH": "true",
        "NEW_RELIC_EXTENSION_PIPELINE_FLUSH": "false",
        "NEW_RELIC_RUNTIME_DONE_GRACE_MS": "1000",
    })
    if new_relic_debug:
        env_vars.update({
            "NEW_RELIC_EXTENSION_LOG_LEVEL": "DEBUG",
            "NEW_RELIC_EXTENSION_SEND_EXTENSION_LOGS": "true",
            "NEW_RELIC_LOG_LEVEL": "debug",
        })
    image_command = ["newrelic_lambda_wrapper.handler"]

# Lambda function — container image from ECR
fn = aws.lambda_.Function(
    "strava-slack-bot",
    name="strava-slack-bot",
    package_type="Image",
    image_uri=image.image_name,
    role=lambda_role.arn,
    architectures=["arm64"],
    timeout=60,
    memory_size=512,
    environment=aws.lambda_.FunctionEnvironmentArgs(variables=env_vars),
    image_config=(
        aws.lambda_.FunctionImageConfigArgs(commands=image_command)
        if image_command
        else None
    ),
)

# Wire SQS → Lambda
aws.lambda_.EventSourceMapping(
    "sqs-trigger",
    event_source_arn=queue.arn,
    function_name=fn.name,
    batch_size=1,
)

pulumi.export("queue_url", queue.url)
pulumi.export("dlq_url", dlq.url)
pulumi.export("ecr_repo", repo.repository_url)
pulumi.export("lambda_name", fn.name)
pulumi.export("new_relic_enabled", new_relic_enabled)
