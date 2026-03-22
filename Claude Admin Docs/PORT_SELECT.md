# PORT_SELECT — Implementing CLI Port Selection in Python Entry Points

## Pattern

Allow the user to optionally pass a port number as the first command-line argument.
Default to a sensible fallback (e.g. 5000) if no argument is given.

```python
import sys

port = 5000
if len(sys.argv) > 1:
    try:
        port = int(sys.argv[1])
    except ValueError:
        print(f"WARNING: Invalid port '{sys.argv[1]}', using default 5000.")
```

Place this block **once**, near the top of the entry point file, immediately after
config loading and before any module imports that might depend on it.

Usage:
```
py run.py          # starts on port 5000
py run.py 5001     # starts on port 5001
```

---

## Critical Rule: One Assignment Only

**Never assign `port` a second time later in the same file.**

A second assignment — even something innocuous like `port = config.get("port", 5000)` —
will silently overwrite the value parsed from `sys.argv`. The sys.argv block will appear
to work (it runs, no error) but the later assignment wins at runtime.

Bad pattern (do not do this):
```python
# Top of file
port = 5000
if len(sys.argv) > 1:
    port = int(sys.argv[1])   # ← correct

# ... later ...
port = config.get("port", 5000)   # ← OVERWRITES sys.argv value — BUG
```

---

## Verification Checklist

After adding port selection, verify with these two checks:

1. **Grep for all port assignments in the file:**
   ```
   # PowerShell
   Select-String "port\s*=" run.py

   # bash
   grep "port\s*=" run.py
   ```
   There should be exactly **one** assignment block (`port = 5000` + `port = int(...)`).
   Any other `port =` line is a bug unless it's inside the same if/try block.

2. **Run with a non-default port and confirm the banner and server both use it:**
   ```
   py run.py 5001
   ```
   The startup banner should print `http://127.0.0.1:5001` and the server
   should respond at that address.

---

## Optional: Config-File Port as Fallback

If you want to support a port in `config.json` as well as a CLI arg, do it in
**one** place and keep the precedence explicit:

```python
config_port = config.get("port", 5000)

port = config_port
if len(sys.argv) > 1:
    try:
        port = int(sys.argv[1])   # CLI arg overrides config
    except ValueError:
        print(f"WARNING: Invalid port '{sys.argv[1]}', using config/default {config_port}.")
```

Do not split this into two separate assignments. Mixing two sources is where
silent overwrite bugs are born.

---

## Applicable To

Any Python entry point that starts a local web server (Flask, FastAPI, http.server, etc.)
where the user may need to run multiple instances or avoid port conflicts.
