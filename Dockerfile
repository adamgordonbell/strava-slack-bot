FROM public.ecr.aws/lambda/python:3.13

COPY app/ ${LAMBDA_TASK_ROOT}/

CMD ["handler.handler"]
