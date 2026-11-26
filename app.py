import os
import socket
import time
import hashlib
from flask import Flask, jsonify, render_template_string, request
import redis

app = Flask(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
CLUSTER_NAME = os.getenv("CLUSTER_NAME", "Local Docker")
CLOUD_ENV = os.getenv("CLOUD_ENV", "Container Environment")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloud Visitor Counter</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f8fafc;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: rgba(30, 41, 59, 0.9);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 16px;
            padding: 36px;
            max-width: 540px;
            width: 100%;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
        }
        .badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            margin-bottom: 16px;
        }
        h1 {
            font-size: 26px;
            margin-bottom: 8px;
            color: #ffffff;
        }
        .subtitle {
            color: #94a3b8;
            font-size: 14px;
            margin-bottom: 28px;
        }
        .counter-box {
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            margin-bottom: 24px;
        }
        .counter-label {
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #94a3b8;
            margin-bottom: 8px;
        }
        .counter-value {
            font-size: 54px;
            font-weight: 700;
            color: #38bdf8;
            line-height: 1.1;
        }
        .meta {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 24px;
        }
        .meta-item {
            background: rgba(15, 23, 42, 0.55);
            border: 1px solid rgba(148, 163, 184, 0.15);
            border-radius: 10px;
            padding: 12px;
        }
        .meta-key {
            font-size: 11px;
            color: #94a3b8;
            text-transform: uppercase;
            margin-bottom: 4px;
        }
        .meta-val {
            font-size: 14px;
            font-weight: 600;
            color: #e2e8f0;
            word-break: break-all;
        }
        .actions {
            display: flex;
            gap: 12px;
        }
        .btn {
            flex: 1;
            padding: 12px 16px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            text-align: center;
        }
        .btn-primary {
            background: #0284c7;
            color: white;
        }
        .btn-primary:hover { background: #0369a1; }
        .btn-secondary {
            background: rgba(148, 163, 184, 0.15);
            color: #e2e8f0;
            border: 1px solid rgba(148, 163, 184, 0.25);
        }
        .btn-secondary:hover { background: rgba(148, 163, 184, 0.25); }
        .error {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #fca5a5;
            padding: 16px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="badge">{{ cloud_env }}</div>
        <h1>Visitor Counter Web App</h1>
        <p class="subtitle">Flask + Redis deployed on Docker &amp; Kubernetes</p>

        {% if error %}
        <div class="error">
            <strong>Redis Connection Error:</strong> {{ error }}
        </div>
        {% else %}
        <div class="counter-box">
            <div class="counter-label">Total Visitors</div>
            <div class="counter-value">{{ visits }}</div>
        </div>
        {% endif %}

        <div class="meta">
            <div class="meta-item">
                <div class="meta-key">Served By Pod / Host</div>
                <div class="meta-val">{{ hostname }}</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">Cluster</div>
                <div class="meta-val">{{ cluster_name }}</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">Redis Host</div>
                <div class="meta-val">{{ redis_host }}:{{ redis_port }}</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">Timestamp (UTC)</div>
                <div class="meta-val">{{ timestamp }}</div>
            </div>
        </div>

        <div class="actions">
            <a class="btn btn-primary" href="/">Refresh (+1 Visit)</a>
            <a class="btn btn-secondary" href="/api/visits">JSON API</a>
        </div>
    </div>
</body>
</html>
"""


def get_metadata():
    """Return runtime metadata identifying the serving pod and cluster."""
    return {
        "hostname": socket.gethostname(),
        "cluster": CLUSTER_NAME,
        "environment": CLOUD_ENV,
        "redis_host": REDIS_HOST,
        "redis_port": REDIS_PORT,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
    }


@app.route("/")
def index():
    """Increment the visitor counter in Redis and render the dashboard."""
    meta = get_metadata()
    try:
        visits = redis_client.incr("visitor_count")
        return render_template_string(
            HTML_TEMPLATE,
            visits=visits,
            error=None,
            hostname=meta["hostname"],
            cluster_name=meta["cluster"],
            cloud_env=meta["environment"],
            redis_host=meta["redis_host"],
            redis_port=meta["redis_port"],
            timestamp=meta["timestamp"],
        )
    except redis.RedisError as exc:
        return (
            render_template_string(
                HTML_TEMPLATE,
                visits=None,
                error=str(exc),
                hostname=meta["hostname"],
                cluster_name=meta["cluster"],
                cloud_env=meta["environment"],
                redis_host=meta["redis_host"],
                redis_port=meta["redis_port"],
                timestamp=meta["timestamp"],
            ),
            503,
        )


@app.route("/api/visits")
def api_visits():
    """Increment and return the visitor count as JSON."""
    meta = get_metadata()
    try:
        visits = redis_client.incr("visitor_count")
        return jsonify({"visits": visits, **meta}), 200
    except redis.RedisError as exc:
        return jsonify({"error": str(exc), **meta}), 503


@app.route("/stress")
def stress():
    """Perform bounded CPU work to verify Kubernetes HPA autoscaling."""
    iterations = min(int(request.args.get("iterations", "50000")), 500000)
    data = b"cloud-computing-hpa-load-test"
    for _ in range(iterations):
        data = hashlib.sha256(data).digest()
    return jsonify(
        {
            "status": "completed",
            "iterations": iterations,
            "digest_prefix": data.hex()[:12],
            **get_metadata(),
        }
    ), 200


@app.route("/health")
def health():
    """Readiness and health check verifying Redis connectivity."""
    try:
        redis_client.ping()
        return jsonify({"status": "healthy", **get_metadata()}), 200
    except redis.RedisError as exc:
        return jsonify({"status": "unhealthy", "error": str(exc), **get_metadata()}), 503


@app.route("/live")
def liveness():
    """Liveness probe confirming the Flask process is responsive."""
    return jsonify({"status": "alive", **get_metadata()}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
