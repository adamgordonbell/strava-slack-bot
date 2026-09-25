# New Relic Lambda layer as an image: Python agent + newrelic_lambda wrapper
# + the Lambda extension binary, all under /opt. Python version in the tag
# (313) must match the base image below; -arm64 matches the Lambda arch.
FROM public.ecr.aws/newrelic-lambda-layers-for-docker/newrelic-lambda-layers-python:313-arm64 AS newrelic

FROM python:3.13-slim

RUN pip install --no-cache-dir awslambdaric boto3

# Lambda starts anything in /opt/extensions; the agent lives in /opt/python.
COPY --from=newrelic /opt/ /opt/
# python:slim is not the AWS base image, so put the layer on the path by hand.
ENV PYTHONPATH=/opt/python/lib/python3.13/site-packages:/app

COPY app/ /app/
WORKDIR /app

ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
# Plain handler by default. When a New Relic licence key is configured, the
# Pulumi program overrides this with newrelic_lambda_wrapper.handler.
CMD ["handler.handler"]
