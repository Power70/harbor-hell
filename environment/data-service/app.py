import os
from flask import Flask, request, jsonify
from models import db, Item
from celery import Celery

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:////data/app.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

broker_url = os.getenv("BROKER_URL", "redis://redis:6379/0")
celery_app = Celery(broker=broker_url)


@app.before_first_request
def initialise_database():
    db.create_all()


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/items", methods=["POST"])
def create_item():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    item = Item(name=data["name"], value=data.get("value", ""))
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@app.route("/items", methods=["GET"])
def list_items():
    items = Item.query.all()
    return jsonify([i.to_dict() for i in items])


@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "no-message")
    celery_app.send_task(
        "tasks.send_notification",
        args=[message],
        queue="celery",
    )
    return jsonify({"status": "enqueued", "message": message})
