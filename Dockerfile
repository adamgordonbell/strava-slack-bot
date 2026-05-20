FROM python:3.13-slim

RUN pip install --no-cache-dir awslambdaric

COPY app/ /app/
WORKDIR /app

ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD ["handler.handler"]
