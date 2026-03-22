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
# Port selection
# ---------------------------------------------------------------------------
try:
    port_input = input("Enter port to run on [default: 5000]: ").strip()
    port = int(port_input) if port_input else 5000
except ValueError:
    print(f"Invalid port '{port_input}', using default 5000.")
    port = 5000

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
