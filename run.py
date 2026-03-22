import json
import sys

# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------
try:
    with open("config.json") as f:
        config = json.load(f)
except FileNotFoundError:
    print("ERROR: config.json not found.")
    print("Please copy config.json.example to config.json and add your search URLs.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Port selection  (optional first argument: py run.py 5001)
# ---------------------------------------------------------------------------
port = 5000
if len(sys.argv) > 1:
    try:
        port = int(sys.argv[1])
    except ValueError:
        print(f"WARNING: Invalid port '{sys.argv[1]}', using default 5000.")

# ---------------------------------------------------------------------------
# Initialise DB and scheduler
# ---------------------------------------------------------------------------
from thrift_tracker import db, scheduler

db.init_db()
scheduler.start_scheduler(config)

# ---------------------------------------------------------------------------
# Startup banner
# ---------------------------------------------------------------------------
print("==========================================")
print(f" Thrift Tracker running at http://127.0.0.1:{port}")
print(" Press Ctrl+C to stop.")
print("==========================================")

# ---------------------------------------------------------------------------
# Start Flask
# ---------------------------------------------------------------------------
from thrift_tracker.api import app

app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
