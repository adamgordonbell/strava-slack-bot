#!/usr/bin/env bash
# Build container, push to ECR, then run pulumi up
set -euo pipefail

REGION=${AWS_REGION:-us-east-1}
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REPO="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/strava-slack-bot"

echo "==> Logging in to ECR"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"

echo "==> Building image"
docker build --platform linux/arm64 -t strava-slack-bot:latest "$(git rev-parse --show-toplevel)"

echo "==> Tagging and pushing"
docker tag strava-slack-bot:latest "$REPO:latest"
docker push "$REPO:latest"

echo "==> pulumi up"
cd "$(git rev-parse --show-toplevel)/infra"
pulumi up
