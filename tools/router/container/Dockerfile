FROM python:3.12-alpine

WORKDIR /app

RUN pip install --no-cache-dir passlib

COPY tools/router /app/router

EXPOSE 9787

ENTRYPOINT ["python3", "/app/router/router_metrics_exporter.py"]
