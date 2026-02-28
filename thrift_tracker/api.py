import json
import os
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from thrift_tracker import db
from thrift_tracker import runner

# import_links.py lives at the repo root — pull in shared helpers
sys.path.insert(0, str(Path(__file__).parent.parent))
from import_links import detect_site, append_to_thrift_links  # noqa: E402

_LINKS_PATH = Path(__file__).parent.parent / "thrift-links.txt"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_CONFIG_PATH = Path(__file__).parent.parent / "config.json"

if not _CONFIG_PATH.exists():
    raise RuntimeError(
        "config.json not found. "
        "Please copy config.json.example to config.json and add your search URLs."
    )

with open(_CONFIG_PATH) as _f:
    config = json.load(_f)

db.init_db()

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
_STATIC_DIR = Path(__file__).parent.parent / "static"

app = Flask(__name__, static_folder=str(_STATIC_DIR))

_scrape_running = threading.Event()


@app.after_request
def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(str(_STATIC_DIR), "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(str(_STATIC_DIR), filename)


@app.route("/api/listings")
def get_listings():
    max_age_days = int(request.args.get("max_age_days", config.get("max_age_days", 30)))
    listings = db.get_new_listings(max_age_days=max_age_days)
    return jsonify(listings)


@app.route("/api/listings/reviewed", methods=["POST"])
def mark_reviewed():
    data = request.get_json(force=True)
    ids = data.get("ids", [])
    db.mark_reviewed(ids)
    return jsonify({"ok": True})


@app.route("/api/scrape", methods=["POST"])
def start_scrape():
    if _scrape_running.is_set():
        return jsonify({"status": "busy"})

    def _run():
        _scrape_running.set()
        try:
            runner.run_scrape(config)
        finally:
            _scrape_running.clear()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"status": "started"})


@app.route("/api/status")
def status():
    last_run = db.get_last_run()
    return jsonify({"last_run": last_run})


@app.route("/api/save-link", methods=["POST", "OPTIONS"])
def save_link():
    """Append a URL to thrift-links.txt under its auto-detected [site] heading.

    Called by the Thrift Tracker Firefox extension.
    Body: {"url": "https://..."}
    Returns: {"ok": true, "site": "vinted"} or {"ok": false, "error": "..."}
    """
    if request.method == "OPTIONS":
        # CORS preflight
        return "", 204

    data = request.get_json(force=True) or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"ok": False, "error": "No URL provided."}), 400

    site = detect_site(url)
    if not site:
        return jsonify({
            "ok": False,
            "error": "Domain not recognised — not a supported site.",
        }), 400

    written = append_to_thrift_links(_LINKS_PATH, url, site)
    if written:
        return jsonify({"ok": True, "site": site})
    return jsonify({"ok": False, "error": "URL already in thrift-links.txt."}), 409
