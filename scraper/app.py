"""Flask-Dashboard — nur Status-Anzeige + Pause/Resume. Kein DB-Write."""
from __future__ import annotations

import logging
from flask import Flask, jsonify, request, render_template

from scraper.worker import worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

app = Flask(__name__)


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/state")
def api_state():
    return jsonify(worker.get_state())


@app.route("/api/summary")
def api_summary():
    return jsonify(worker.get_summary())


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    data = request.get_json(force=True)
    series_ids = [int(s) for s in data.get("series_ids", [])]
    delay = float(data.get("delay", 3.0))
    if not series_ids:
        return jsonify({"error": "series_ids erforderlich"}), 400
    worker.delay = delay
    worker.enqueue(series_ids)
    return jsonify({"enqueued": series_ids})


@app.route("/api/pause", methods=["POST"])
def api_pause():
    worker.pause()
    return jsonify({"status": "paused"})


@app.route("/api/resume", methods=["POST"])
def api_resume():
    worker.resume()
    return jsonify({"status": "running"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)