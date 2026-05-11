"""
SMC Bridge Server v5 — accepts SL from TradingView, EA calculates TP
"""

from flask import Flask, request, jsonify
import os
import datetime

app = Flask(__name__)

SECRET = os.environ.get("BRIDGE_SECRET", "smcvantage2024")
latest_signal = {}

ACTION_MAP = {
    "buy":        "BUY",
    "sell":       "SELL",
    "long":       "BUY",
    "short":      "SELL",
    "buy!":       "BUY",
    "sell!":      "SELL",
    "closelong":  "CLOSE",
    "closeshort": "CLOSE",
    "close":      "CLOSE",
}

@app.route("/webhook", methods=["POST"])
def webhook():
    global latest_signal

    raw = request.get_data(as_text=True)
    print(f"RAW: {raw}")

    try:
        data = request.get_json(force=True)
    except Exception as e:
        print(f"JSON ERROR: {e} | RAW: {raw}")
        return jsonify({"error": "Invalid JSON", "raw": raw}), 400

    if data is None:
        return jsonify({"error": "Empty JSON", "raw": raw}), 400

    print(f"PARSED: {data}")

    # Validate secret
    if data.get("secret") != SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    # Validate required fields
    for field in ["action", "symbol", "price"]:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Normalize action
    raw_action = str(data["action"]).lower().strip()
    action = ACTION_MAP.get(raw_action)
    if action is None:
        if "buy" in raw_action or "long" in raw_action:
            action = "BUY"
        elif "sell" in raw_action or "short" in raw_action:
            action = "SELL"
        elif "close" in raw_action:
            action = "CLOSE"
        else:
            return jsonify({"error": f"Unknown action: {data['action']}"}), 400

    # SL from TradingView (optional — EA uses it if provided)
    sl = float(data["sl"]) if "sl" in data and data["sl"] else 0.0

    latest_signal = {
        "action":    action,
        "symbol":    str(data["symbol"]).upper().strip(),
        "price":     float(data["price"]),
        "sl":        sl,
        "lot":       0.02,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "consumed":  False
    }

    print(f"SIGNAL OK: {latest_signal}")
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
