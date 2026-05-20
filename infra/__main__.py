import json
import pulumi
import pulumi_aws as aws
import pulumi_docker as docker

config = pulumi.Config()
slack_bot_token = config.require_secret("slackBotToken")
slack_channel = config.get("slackChannel") or "#bot-testing"

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
    image_name=repo.repository_url,
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
    visibility_timeout_seconds=30,
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

# Lambda function — container image from ECR
fn = aws.lambda_.Function(
    "strava-slack-bot",
    name="strava-slack-bot",
    package_type="Image",
    image_uri=image.image_name,
    role=lambda_role.arn,
    timeout=30,
    memory_size=256,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "SLACK_BOT_TOKEN": slack_bot_token,
            "SLACK_CHANNEL": slack_channel,
        }
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
