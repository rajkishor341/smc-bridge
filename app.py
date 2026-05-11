"""
SMC Bridge Server — receives TradingView webhooks and writes signal.json
Deploy this on Render.com (free tier) — no Python needed on your PC.
"""

from flask import Flask, request, jsonify
import os
import datetime

app = Flask(__name__)

SECRET = os.environ.get("BRIDGE_SECRET", "smcvantage2024")
latest_signal = {}

@app.route("/webhook", methods=["POST"])
def webhook():
    global latest_signal

    # Log raw body first for debugging
    raw = request.get_data(as_text=True)
    print(f"Raw webhook body: {raw}")

    try:
        data = request.get_json(force=True)
    except Exception as e:
        print(f"JSON parse error: {e} | Body: {raw}")
        return jsonify({"error": "Invalid JSON", "body": raw}), 400

    if data is None:
        print(f"Empty or non-JSON body: {raw}")
        return jsonify({"error": "Empty or invalid JSON", "body": raw}), 400

    print(f"Parsed data: {data}")

    # Validate secret
    if data.get("secret") != SECRET:
        print(f"Auth failed. Got secret: {data.get('secret')}")
        return jsonify({"error": "Unauthorized"}), 403

    # Validate required fields
    for field in ["action", "symbol", "price"]:
        if field not in data:
            print(f"Missing field: {field}")
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Normalize action — handle buy/sell/BUY/SELL from TradingView
    action = str(data["action"]).upper().strip()
    if action not in ["BUY", "SELL", "CLOSE"]:
        print(f"Invalid action: {data['action']}")
        return jsonify({"error": f"Invalid action: {data['action']}"}), 400

    # Build signal
    latest_signal = {
        "action":    action,
        "symbol":    str(data["symbol"]).upper().strip(),
        "price":     float(data["price"]),
        "lot":       0.02,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "consumed":  False
    }

    print(f"Signal accepted: {latest_signal}")
    return jsonify({"status": "ok", "signal": latest_signal}), 200


@app.route("/signal", methods=["GET"])
def get_signal():
    global latest_signal
    if not latest_signal or latest_signal.get("consumed"):
        return jsonify({"action": "NONE"}), 200
    latest_signal["consumed"] = True
    return jsonify(latest_signal), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running", "last_signal": latest_signal}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
