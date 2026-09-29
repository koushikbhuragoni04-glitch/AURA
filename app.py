"""Flask API + UI:  python app.py  ->  http://localhost:5000"""
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory

import agent
import memory
from seed_data import DEMO_ALERT

app = Flask(__name__, static_folder="static")
memory.ensure_bank()


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/demo-alert")
def demo_alert():
    return jsonify({"alert": DEMO_ALERT})


@app.post("/api/triage")
def triage():
    alert = (request.json or {}).get("alert", "").strip()
    if not alert:
        return jsonify({"error": "alert text is required"}), 400
    try:
        return jsonify(agent.triage(alert))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/resolve")
def resolve():
    """Close the loop: the engineer tells the agent what really happened -> retained in Hindsight."""
    d = request.json or {}
    required = ["service", "title", "symptoms", "root_cause", "resolution"]
    if any(not str(d.get(k, "")).strip() for k in required):
        return jsonify({"error": f"required fields: {', '.join(required)}"}), 400
    now = datetime.utcnow()
    inc = {
        "id": "INC-" + now.strftime("%y%m%d%H%M%S"),
        "service": d["service"], "title": d["title"], "symptoms": d["symptoms"],
        "root_cause": d["root_cause"], "resolution": d["resolution"],
        "failed": d.get("failed", ""), "agent_feedback": d.get("agent_feedback", ""),
        "ttr_minutes": d.get("ttr_minutes") or "unknown", "engineer": d.get("engineer") or "on-call",
    }
    try:
        memory.retain_incident(inc, when=now)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True, "id": inc["id"]})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
