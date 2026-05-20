#!/usr/bin/env bash
# Deploy everything — Pulumi builds and pushes the container image as part of the stack
set -euo pipefail

cd "$(git rev-parse --show-toplevel)/infra"
pulumi up
