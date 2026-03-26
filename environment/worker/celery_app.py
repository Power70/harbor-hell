import os
from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost//")

app = Celery(
    "worker",
    broker=broker_url,
    backend=broker_url,
    include=["tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
