# Thrift Tracker — Session Instructions for Claude Code

You are building **Thrift Tracker**: a locally-run web application that periodically scrapes
a user-defined list of secondhand clothing search URLs, stores new listings in a SQLite
database, and presents them in a browser UI where the user can review, check, and open
listings for purchase.

Work through the prompts below **in strict order**. Do not skip ahead. After completing
each numbered prompt, commit all changes to GitHub with the commit message specified,
then proceed to the next prompt automatically. Only pause and wait for user input when a
prompt explicitly says **[USER INPUT REQUIRED]**.

Assume the working directory is the repository root for all relative paths.

---

## Environment assumptions
- Python 3.11+
- Node is NOT required; all frontend assets are plain HTML/CSS/JS served by Flask.
- The user is on macOS or Linux.
- Git is initialised and a remote named `origin` already exists.
- You may install Python packages with `pip install`.

---

## Prompt 0 — Load Notifications Specification

Before writing any code, read the file `SAR-notifications-pwa.md` from
the project context. Confirm you have read it by listing the six component
names described in the COMPONENTS section. These requirements are mandatory
and must be woven into the build steps that follow — do not treat them as
an optional add-on to be handled at the end.

---

## Prompt 1 — Repository scaffold and dependencies

1. Create the following directory structure (create empty `__init__.py` files where noted):

```
thrift_tracker/
  __init__.py
  scraper/
    __init__.py
    base.py
    vinted.py
    depop.py
    ebay.py
    poshmark.py
  db.py
  scheduler.py
  runner.py
  api.py
static/
  index.html
  app.js
  style.css
config.json.example
requirements.txt
run.py
.gitignore
```

2. Populate `requirements.txt` with:

```
flask>=3.0
playwright>=1.44
apscheduler>=3.10
python-dotenv>=1.0
```

3. Populate `.gitignore` with at minimum:

```
__pycache__/
*.pyc
*.db
.env
config.json
```

4. Populate `config.json.example` with the following template. Do not create `config.json`
   itself (it is gitignored; the user will create it from this example):

```json
{
  "searches": [
    {
      "label": "Levi 501 W28",
      "url": "https://www.vinted.co.uk/catalog?search_text=levi+501&size_ids[]=1234",
      "site": "vinted"
    },
    {
      "label": "Vintage Carhartt Jacket M",
      "url": "https://www.depop.com/search/?q=carhartt+vintage+jacket&size=M",
      "site": "depop"
    },
    {
      "label": "Levi 501 eBay",
      "url": "https://www.ebay.co.uk/sch/i.html?_nkw=levi+501+w28",
      "site": "ebay"
    },
    {
      "label": "Carhartt Poshmark",
      "url": "https://poshmark.com/search?query=carhartt+jacket&size%5B%5D=M&category=Men",
      "site": "poshmark"
    }
  ],
  "schedule": {
    "days_of_week": ["tue", "fri"],
    "hour": 8,
    "minute": 0
  },
  "max_age_days": 30
}
```

5. Write `README.md` covering:
   - What the app does (scrapes bookmarked secondhand clothing searches twice a week,
     surfaces new listings in a local UI for manual review).
   - Setup steps:
     ```
     pip install -r requirements.txt
     playwright install chromium
     cp config.json.example config.json
     # Edit config.json with your own search URLs and preferred schedule
     python run.py
     ```
   - How to populate `config.json`: for each saved search, paste the full URL from your
     browser address bar and set the `site` field to one of:
     `vinted`, `depop`, `ebay`, `poshmark`.
   - How the scheduler works (runs automatically on the configured days/time in UTC;
     also available as a manual trigger via the UI).
   - A section titled "Adding more sites" explaining that Grailed, Mercari,
     Vestiaire Collective, ThredUp, and ASOS Marketplace are good candidates; a new
     scraper only requires implementing the `BaseScraper` interface in
     `thrift_tracker/scraper/` and registering it in `thrift_tracker/scraper/__init__.py`.

**Commit message:** `feat: initial repository scaffold`

---

## Prompt 2 — Database layer

Implement `thrift_tracker/db.py`. Requirements:

1. Use Python's built-in `sqlite3` module only. No ORM. Database file path:
   `thrift_tracker.db` in the repository root (already gitignored).

2. On first run, create two tables if they do not exist:

   **listings**
   | column | type | notes |
   |---|---|---|
   | id | INTEGER PRIMARY KEY AUTOINCREMENT | |
   | site | TEXT NOT NULL | e.g. "vinted" |
   | listing_id | TEXT NOT NULL | site-native unique identifier |
   | label | TEXT | search label this listing came from |
   | title | TEXT | |
   | size | TEXT | |
   | price | TEXT | |
   | image_url | TEXT | |
   | listing_url | TEXT NOT NULL | |
   | seen_at | TEXT | ISO-8601 UTC datetime, set automatically on insert |
   | reviewed | INTEGER DEFAULT 0 | 0 = new, 1 = user has opened/dismissed |

   Add a UNIQUE constraint on `(site, listing_id)`.

   **runs**
   | column | type | notes |
   |---|---|---|
   | id | INTEGER PRIMARY KEY AUTOINCREMENT | |
   | started_at | TEXT | ISO-8601 UTC |
   | finished_at | TEXT | ISO-8601 UTC |
   | new_count | INTEGER | number of new listings found in this run |

3. Expose the following functions at module level:
   - `init_db()` — creates tables if not present; safe to call multiple times.
   - `listing_exists(site: str, listing_id: str) -> bool`
   - `insert_listing(data: dict) -> bool` — inserts if not present, sets `seen_at` to
     current UTC time; returns `True` if inserted, `False` if already known.
   - `get_new_listings(max_age_days: int = 30) -> list[dict]` — returns all rows where
     `reviewed = 0` and `seen_at` is within `max_age_days` days of now, ordered newest
     first. Each dict should include all column names as keys.
   - `mark_reviewed(listing_ids: list[int])` — sets `reviewed = 1` for given row IDs.
   - `log_run(started_at: str, finished_at: str, new_count: int)`
   - `get_last_run() -> dict | None` — returns the most recent row from `runs`, or
     `None` if no runs exist.

4. Write a small self-test block under `if __name__ == "__main__"` that:
   - Calls `init_db()`.
   - Inserts a dummy listing.
   - Asserts `listing_exists` returns `True` for it.
   - Prints "DB OK".

**Commit message:** `feat: database layer`

---

## Prompt 3 — Scraper base class

Implement `thrift_tracker/scraper/base.py`.

1. Define an abstract base class `BaseScraper` using Python's `abc` module.

2. Constructor signature: `__init__(self, search_config: dict)` where `search_config`
   is one entry from the `searches` array in `config.json`. Store as `self.config`.

3. Define one abstract method:
   ```python
   def fetch_listings(self) -> list[dict]:
       ...
   ```
   Each returned dict must contain at minimum these keys (use `None` where unavailable):
   ```
   listing_id   # str — unique on that platform
   title        # str
   size         # str | None
   price        # str | None  e.g. "£24.00"
   image_url    # str | None
   listing_url  # str — absolute URL
   ```

4. Provide a concrete helper `launch_browser(self) -> tuple`:
   - Launches a headless Playwright Chromium browser using `sync_playwright`.
   - Sets a realistic desktop user-agent string.
   - Returns `(playwright_instance, browser, page)` so callers can close all three.

5. Provide a helper `safe_text(self, locator) -> str | None` that calls `.inner_text()`
   on a Playwright locator and returns `None` on any exception.

**Commit message:** `feat: scraper base class`

---

## Prompt 4 — Vinted scraper

Implement `thrift_tracker/scraper/vinted.py`.

1. Class `VintedScraper(BaseScraper)`.

2. Implement `fetch_listings()`:
   - Launch the browser via `self.launch_browser()`.
   - Navigate to `self.config["url"]`.
   - Handle the Vinted cookie consent banner: if a consent/accept button is present
     within 5 seconds, click it.
   - Wait for listing cards to appear. Vinted typically uses a grid where each card
     is a `<div>` or `<article>` containing an item link. Inspect the live page to
     find the correct selector; add a comment noting the selector and the date it was
     verified.
   - For each card (up to 48), extract:
     - `listing_id`: numeric ID parsed from the card link href
       (e.g. `/items/1234567890-title` → `"1234567890"`).
     - `title`: item name.
     - `size`: size badge text if present, else `None`.
     - `price`: price text.
     - `image_url`: `src` of the first `<img>` inside the card.
     - `listing_url`: absolute URL of the card link.
   - Close playwright, browser, and page in a `finally` block.
   - On any exception, print `[VintedScraper] ERROR: {e}` and return `[]`.

**Commit message:** `feat: Vinted scraper`

---

## Prompt 5 — Depop scraper

Implement `thrift_tracker/scraper/depop.py`.

1. Class `DepopScraper(BaseScraper)`.

2. Implement `fetch_listings()`:
   - Navigate to `self.config["url"]`.
   - Depop is a heavily client-side React app. Wait up to 10 seconds for product tiles
     to appear. The selector has historically been `article[data-testid="product-card"]`
     or a `<li>` wrapping a product thumbnail link. Inspect the live page and use the
     correct selector; note it with the verification date in a comment.
   - For each card (up to 48), extract:
     - `listing_id`: from the product link href. Use the full path slug as the ID
       (e.g. `/products/username-some-item-abc123/` → `"username-some-item-abc123"`).
     - `title`: product name text.
     - `size`: size label if present, else `None`.
     - `price`: price text.
     - `image_url`: first `<img>` src or `data-src`.
     - `listing_url`: absolute URL.
   - Handle any cookie/age-gate overlay by dismissing it before scraping.
   - Close all playwright resources in `finally`. Return `[]` on exception with a log.

**Commit message:** `feat: Depop scraper`

---

## Prompt 6 — eBay scraper

Implement `thrift_tracker/scraper/ebay.py`.

1. Class `EbayScraper(BaseScraper)`.

2. Implement `fetch_listings()`:
   - Navigate to `self.config["url"]`.
   - eBay search result items are `<li class="s-item">` elements. Each contains:
     - `<a class="s-item__link">` — the listing URL.
     - `<span class="s-item__title">` — the title.
     - `<span class="s-item__price">` — the price.
   - Inspect the live page and adjust selectors if needed; note any changes with the
     verification date in a comment.
   - For each item (up to 48), extract:
     - `listing_id`: eBay item number from the URL path
       (e.g. `/itm/123456789012` → `"123456789012"`).
     - `title`: strip any "New Listing" prefix eBay adds to some titles.
     - `size`: attempt to read from a secondary info element; use `None` if absent.
     - `price`: price span text.
     - `image_url`: `<img>` src. If src is a base64 placeholder, use `data-src` instead.
     - `listing_url`: the item link href, stripped of all tracking query parameters
       (keep only the path up to and including the item number).
   - Skip the first result if its title is "Shop on eBay" (a promoted placeholder).
   - Close all playwright resources in `finally`. Return `[]` on exception with a log.

**Commit message:** `feat: eBay scraper`

---

## Prompt 7 — Poshmark scraper

Implement `thrift_tracker/scraper/poshmark.py`.

1. Class `PoshmarkScraper(BaseScraper)`.

2. Implement `fetch_listings()`:
   - Navigate to `self.config["url"]`.
   - Poshmark renders listing tiles in a results grid. Inspect the live page for the
     current card selector (historically `div[data-et-name="listing"]` or a `<div>`
     with class containing `"card"` inside the search results container). Note the
     selector and verification date in a comment.
   - For each card (up to 48), extract:
     - `listing_id`: the alphanumeric slug at the end of the listing URL path.
     - `title`: item title text.
     - `size`: size label if present, else `None`.
     - `price`: price text.
     - `image_url`: first `<img>` src or `data-src`.
     - `listing_url`: absolute URL of the listing.
   - If a login prompt or modal appears and cannot be dismissed, print a warning:
     `[PoshmarkScraper] WARNING: Login prompt may be blocking results.` and return `[]`.
   - Close all playwright resources in `finally`. Return `[]` on exception with a log.

**Commit message:** `feat: Poshmark scraper`

---

## Prompt 8 — Scraper registry and run orchestration

1. In `thrift_tracker/scraper/__init__.py`, define the registry:

```python
from .vinted import VintedScraper
from .depop import DepopScraper
from .ebay import EbayScraper
from .poshmark import PoshmarkScraper

SCRAPERS = {
    "vinted": VintedScraper,
    "depop": DepopScraper,
    "ebay": EbayScraper,
    "poshmark": PoshmarkScraper,
}
```

2. Implement `thrift_tracker/runner.py` with a function `run_scrape(config: dict) -> int`:
   - Call `db.init_db()`.
   - Record `started_at = datetime.utcnow().isoformat()`.
   - Initialise `new_count = 0`.
   - Wrap the entire scrape loop in a `try/except` block (see notification requirements
     below).
   - For each entry in `config["searches"]`:
     - Look up the scraper class from `SCRAPERS`. If the site key is not found, print
       `[runner] WARNING: Unknown site "{site}", skipping.` and continue.
     - Instantiate the scraper with the search config dict and call `fetch_listings()`.
     - For each returned listing dict, add the `site` and `label` keys from the search
       config, then call `db.insert_listing(listing)`. Increment `new_count` if it
       returns `True`.
     - Print: `[{site}] "{label}" → {n} new listing(s)`.
     - If a scraper returns an empty list after previously returning results, or if its
       output suggests a CAPTCHA or login wall (e.g. zero results across multiple
       consecutive runs for a search that historically returns results), call the
       manual-step notification described below.
   - Record `finished_at` and call `db.log_run(started_at, finished_at, new_count)`.
   - Print: `[runner] Run complete. {new_count} new listing(s) total.`
   - Return `new_count`.

3. After writing `run_scrape()`, add the following three lines to import and
   call the ntfy notification utility. The path assumes `ntfy-monitor` is a
   sibling directory to this project; adjust if the actual path differs:

   ```python
   import sys
   sys.path.insert(0, '../ntfy-monitor')  # path to the ntfy-monitor repo
   import notify
   ```

4. At the end of `run_scrape()`, after a successful run, call:

   ```python
   notify.success(f"{new_count} new listing(s) found.", project="Thrift Tracker")
   ```

5. In the `except` block that catches any unhandled exception from the scrape loop,
   call:

   ```python
   notify.error(f"Scrape failed: {str(e)}", project="Thrift Tracker")
   ```

   After logging the notification, re-raise the exception so it propagates to the
   caller and appears in the console output.

6. Wherever a CAPTCHA, login wall, or other condition requiring manual intervention
   is detected (e.g. a scraper returns the warning string or an empty result
   suggestive of a block), call:

   ```python
   notify.manual_step("Manual action required — check the scraper.", project="Thrift Tracker")
   ```

**Commit message:** `feat: scraper registry, run orchestration, and ntfy notifications`

---

## Prompt 9 — Flask API

Implement `thrift_tracker/api.py`.

Create a Flask application with the following routes:

| Method | Path | Behaviour |
|---|---|---|
| GET | `/` | Serves `static/index.html` |
| GET | `/static/<path:filename>` | Serves files from the `static/` directory |
| GET | `/api/listings` | Returns JSON array of unreviewed listings. Accepts optional query param `max_age_days` (default: value from `config["max_age_days"]`, fallback 30). |
| POST | `/api/listings/reviewed` | Body: `{"ids": [1, 2, 3]}`. Marks those IDs reviewed. Returns `{"ok": true}`. |
| POST | `/api/scrape` | Starts a scrape in a daemon background thread. Returns `{"status": "started"}` immediately. Prevents concurrent runs (if a run is already in progress, return `{"status": "busy"}`). |
| GET | `/api/status` | Returns `{"last_run": <last run dict or null>}`. |

Additional requirements:
- At module load, call `db.init_db()`.
- Load `config.json` at module load. If missing, raise a `RuntimeError` with a message
  directing the user to copy `config.json.example`.
- Add an `after_request` hook that sets `Access-Control-Allow-Origin: *` on all responses.
- Use a module-level `threading.Event` called `_scrape_running` to guard against
  concurrent scrape runs.

**Commit message:** `feat: Flask API`

---

## Prompt 10 — Scheduler

Implement `thrift_tracker/scheduler.py`.

1. Use `APScheduler`'s `BackgroundScheduler` with a `CronTrigger`.

2. Expose `start_scheduler(config: dict)`:
   - Read `config["schedule"]`: `days_of_week` (list of 3-letter day strings),
     `hour` (int), `minute` (int).
   - Add a cron job that calls `runner.run_scrape(config)` on those days and times (UTC).
   - Start the scheduler (non-blocking).
   - Print: `[scheduler] Scrape scheduled: {days} at {HH:MM} UTC`

3. Handle `KeyboardInterrupt` gracefully by shutting the scheduler down.

**Commit message:** `feat: scheduler`

---

## Prompt 11 — Entry point

Implement `run.py` at the repository root.

1. Attempt to open and parse `config.json`. If missing, print:
   ```
   ERROR: config.json not found.
   Please copy config.json.example to config.json and add your search URLs.
   ```
   Then exit with code 1.

2. Call `db.init_db()`.

3. Call `scheduler.start_scheduler(config)`.

4. Print the startup banner:
   ```
   ==========================================
    Thrift Tracker running at http://127.0.0.1:5000
    Press Ctrl+C to stop.
   ==========================================
   ```

5. Start the Flask app from `thrift_tracker.api` with `host="127.0.0.1"`, `port=5000`,
   `debug=False`, `use_reloader=False`.

**Commit message:** `feat: entry point`

---

## Prompt 12 — Frontend HTML

Implement `static/index.html` as a complete single-page layout. No framework, no build step.

Structure:
- `<head>`: charset, viewport meta, title "Thrift Tracker", link to `style.css`.
- `<header>`: app title "Thrift Tracker", a **Refresh** button, a **Run Scrape Now**
  button.
- `<div id="status-bar">`: displays last-run timestamp and new listing count; starts
  with placeholder text "Loading status…".
- `<div id="popup-warning" hidden>`: a dismissible banner warning the user to allow
  popups for localhost when opening multiple tabs. Contains a close (×) button.
- `<main id="listings-container">`: empty on load; listing cards injected here by JS.
- `<div id="empty-state" hidden>`: text "No new listings. Run a scrape to check for
  updates."
- `<footer id="action-bar">`: sticky bottom bar containing:
  - `<span id="selected-count">0 selected</span>`
  - **Open Selected** button (`id="btn-open"`, disabled by default)
  - **Mark Reviewed** button (`id="btn-reviewed"`, disabled by default)
- `<script src="app.js">` at end of body.

**Commit message:** `feat: frontend HTML`

---

## Prompt 13 — Frontend JavaScript

Implement `static/app.js` with the following:

**State**
```js
let listings = [];
let selected = new Set();
let lastRunId = null;
let pollInterval = null;
```

**`fetchListings()`**
- `GET /api/listings` → store in `listings` → call `renderListings()`.

**`renderListings()`**
- Clear `#listings-container`.
- Toggle `#empty-state` visibility based on whether `listings` is empty.
- For each listing in `listings`, create a card `<div class="listing-card">` containing:
  - `<input type="checkbox" data-id="{id}">` — checked state driven by `selected`.
  - `<div class="listing-image">` containing an `<img src="{image_url}">` if image
    is available, otherwise a placeholder div with text "No image".
  - `<div class="listing-info">` containing:
    - `<h3>{title}</h3>`
    - `<span class="listing-size">Size: {size ?? "—"}</span>`
    - `<span class="listing-price">{price ?? "—"}</span>`
    - `<span class="listing-label">{label}</span>` (the search name)
    - `<a href="{listing_url}" target="_blank" rel="noopener">View listing ↗</a>`
  - On checkbox change: update `selected`, add/remove `"selected"` class on the card,
    call `updateFooter()`.
- Restore checked state from `selected` after re-render.

**`updateFooter()`**
- Update `#selected-count` text.
- Enable/disable `#btn-open` and `#btn-reviewed` based on `selected.size > 0`.

**`openSelected()`**
- If `selected.size > 1`, show `#popup-warning`.
- For each id in `selected`, find the listing and call `window.open(listing_url, "_blank")`.

**`markReviewed()`**
- `POST /api/listings/reviewed` with `{"ids": [...selected]}`.
- On success: remove reviewed listings from `listings`, clear `selected`, re-render.

**`runScrape()`**
- `POST /api/scrape`.
- If response is `{"status": "busy"}`, update status bar: "Scrape already in progress."
- Otherwise update status bar: "Scrape started — checking for new listings…"
- Start polling `GET /api/status` every 5 seconds. When `last_run.id` changes from
  `lastRunId`, stop polling, call `fetchListings()`, and update status bar with the
  result: "Last scrape: {finished_at} — {new_count} new listing(s) found."

**`fetchStatus()`**
- `GET /api/status` → if `last_run` exists, update `lastRunId` and display in status bar.

**On `DOMContentLoaded`**: call `fetchStatus()` then `fetchListings()`. Wire up all
button click handlers. Wire up the close button on `#popup-warning`.

**Commit message:** `feat: frontend JavaScript`

---

## Prompt 14 — Stylesheet

Implement `static/style.css`.

Design brief:
- Clean, minimal, mobile-friendly layout.
- Colour palette: `#ffffff` background, `#1a1a1a` text, `#2d6a4f` accent (forest green —
  fitting for the sustainable secondhand theme), `#f0f4f2` light tint for card
  backgrounds, `#e63946` for destructive/warning elements.
- Typography: system font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`).
- Header: sticky, white, 1px bottom border, flex layout, `1rem` padding. Title left,
  buttons right.
- `#status-bar`: muted grey text, small font, `0.5rem 1rem` padding, border-bottom.
- `#popup-warning`: yellow background (`#fff3cd`), border, padding, flex with close
  button on the right.
- `#listings-container`: CSS grid, `repeat(auto-fill, minmax(240px, 1fr))`, `1rem` gap,
  `1rem` padding.
- `.listing-card`: white background, `4px` rounded corners, `box-shadow: 0 1px 4px
  rgba(0,0,0,0.1)`, overflow hidden, `transition: box-shadow 0.2s`. Hover: slightly
  deeper shadow.
- `.listing-card.selected`: `4px solid #2d6a4f` left border.
- `.listing-image img`: width 100%, aspect-ratio 1/1, object-fit cover.
- `.listing-info`: `0.75rem` padding, display flex, flex-direction column, gap `0.25rem`.
- `.listing-info h3`: font-size `0.95rem`, margin 0, line-height 1.3.
- `.listing-size`, `.listing-price`: font-size `0.85rem`, color `#555`.
- `.listing-label`: font-size `0.75rem`, color `#2d6a4f`, font-weight 600.
- `.listing-info a`: font-size `0.8rem`, color `#2d6a4f`, margin-top auto.
- `#action-bar` (footer): sticky bottom, white, 1px top border, flex, space-between,
  `0.75rem 1rem` padding, z-index 100.
- Buttons — primary (`.btn-primary`): background `#2d6a4f`, white text, no border,
  `0.5rem 1rem` padding, border-radius `4px`, cursor pointer. Hover: darken 10%.
- Buttons — secondary (`.btn-secondary`): background transparent, `#2d6a4f` text,
  `1px solid #2d6a4f`, same padding/radius. Hover: light green background.
- Disabled button: opacity 0.4, cursor not-allowed.
- `#empty-state`: display flex, align-items center, justify-content center, min-height
  `200px`, color `#999`, font-size `1rem`.
- Responsive: at `max-width: 600px`, grid becomes single column; header buttons shrink
  or stack.

**Commit message:** `feat: stylesheet`

---

## Prompt 15 — Integration checks and final polish

1. Run each of the following checks and fix any errors found before committing:

   ```bash
   python -c "from thrift_tracker import db; db.init_db(); print('DB OK')"
   python -c "from thrift_tracker.api import app; print('API OK')"
   python -c "from thrift_tracker.scraper import SCRAPERS; print(list(SCRAPERS.keys()))"
   python -c "from thrift_tracker import runner; print('Runner OK')"
   ```

   Expected outputs:
   - `DB OK`
   - `API OK`
   - `['vinted', 'depop', 'ebay', 'poshmark']`
   - `Runner OK`

2. Verify `static/index.html` has no broken references to `app.js` or `style.css`.

3. Tidy up: remove any stray debug `print()` statements that were not intentional.
   Ensure all Python files have a trailing newline.

4. Update `README.md` to add a "Known limitations" section:
   - Scraper selectors may need updating if a site redesigns its frontend. Each scraper
     file contains a comment noting when its selectors were last verified.
   - Poshmark may show a login prompt that blocks results; if this occurs the console
     will print a warning.
   - Opening many tabs at once: the browser may block this; allow popups for localhost
     when prompted.
   - All data is stored locally; nothing is sent to any external server.
   - Schedule times are in UTC; adjust `hour` in `config.json` to match your local time.
   - ntfy notifications require the `ntfy-monitor` repository to be present as a sibling
     directory. If it is not found, `run_scrape()` will raise an `ImportError` on first
     run. The path can be adjusted in `thrift_tracker/runner.py`.

5. Stage all files and commit.

**Commit message:** `feat: integration checks, final polish, and README updates`

---

## Done

All prompts are complete. The application is ready. Remind the user of the three steps
needed before first use:

1. `cp config.json.example config.json` — then open `config.json` and replace the
   example URLs with their actual bookmarked search URLs.
2. `playwright install chromium` — if not already installed.
3. `python run.py` — then open `http://127.0.0.1:5000` and click **Run Scrape Now**
   to populate the initial listing set.
