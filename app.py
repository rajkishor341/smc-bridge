"""
SMC Bridge Server — receives TradingView webhooks and writes signal.json
Deploy this on Render.com (free tier) — no Python needed on your PC.
"""

from flask import Flask, request, jsonify
import json
import os
import datetime

app = Flask(__name__)

# Simple secret token to block random bots hitting your URL
# You set this same token in your TradingView alert message
SECRET = os.environ.get("BRIDGE_SECRET", "smcvantage2024")

# In-memory signal store (Render free tier has ephemeral disk)
latest_signal = {}

@app.route("/webhook", methods=["POST"])
def webhook():
    global latest_signal

    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    # Validate secret
    if data.get("secret") != SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    # Validate required fields — sl/tp removed, EA calculates them from ATR on MT5 side
    required = ["action", "symbol", "price"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Validate action
    if data["action"] not in ["BUY", "SELL", "CLOSE"]:
        return jsonify({"error": "action must be BUY, SELL or CLOSE"}), 400

    # Build clean signal — sl/tp calculated by EA on MT5 side using ATR
    latest_signal = {
        "action":    data["action"].upper(),
        "symbol":    data["symbol"].upper(),
        "price":     float(data["price"]),
        "lot":       0.02,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "consumed":  False
    }

    print(f"[{latest_signal['timestamp']}] Signal received: {latest_signal}")
    return jsonify({"status": "ok", "signal": latest_signal}), 200


@app.route("/signal", methods=["GET"])
def get_signal():
    """MT5 EA polls this endpoint every second to get the latest signal."""
    global latest_signal

    if not latest_signal:
        return jsonify({"action": "NONE"}), 200

    # Mark as consumed after first read so EA doesn't double-trade
    if latest_signal.get("consumed"):
        return jsonify({"action": "NONE"}), 200

    latest_signal["consumed"] = True
    return jsonify(latest_signal), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running", "last_signal": latest_signal}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
