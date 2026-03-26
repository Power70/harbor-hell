import os
import redis as redis_client
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "fallback-secret")

jwt = JWTManager(app)

USERS = {
    "testuser": "secret",
    "admin":    "adminpass",
}

_redis = redis_client.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379"),
    decode_responses=True,
)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    if not username or USERS.get(username) != password:
        return jsonify({"error": "Invalid credentials"}), 401

    # Fails at this line if REDIS_URL port is wrong
    _redis.setex(f"session:{username}", 3600, "active")

    token = create_access_token(identity=username)
    return jsonify({"token": token})


@app.route("/validate", methods=["POST"])
def validate():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "")
    return jsonify({"valid": bool(token)})
