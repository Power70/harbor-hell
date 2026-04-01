from celery_app import app


@app.task(name="tasks.send_notification", bind=True, max_retries=3)
def send_notification(self, message: str) -> dict:
    print(f"Task completed successfully: {message}", flush=True)
    return {"status": "done", "message": message}
