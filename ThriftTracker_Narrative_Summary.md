# ThriftTracker Narrative Summary
**Last updated:** 2026Mar22-1400

---

## What Is Thrift Tracker?

Thrift Tracker is a locally-run web application that periodically scrapes a user-defined list of secondhand clothing search URLs across multiple platforms (Vinted, Depop, eBay, Poshmark), stores new listings in a local SQLite database, and presents them in a browser-based UI for manual review. Nothing is sent to any external server — all data stays on your machine.

---

## Application Components

### 1. Entry Point — `run.py`
The script you run to start the application. It:
- Loads `config.json` (exits with a clear error if the file is missing)
- Reads an optional port from the first CLI argument (defaults to 5000)
- Initialises the SQLite database
- Starts the APScheduler background scheduler
- Launches the Flask web server

### 2. Flask API — `thrift_tracker/api.py`
A REST API and static file server. Key endpoints:
- `GET /` — serves the frontend (`static/index.html`)
- `GET /api/listings` — returns unreviewed listings (accepts `max_age_days` query param)
- `POST /api/listings/reviewed` — marks a set of listings as reviewed
- `POST /api/scrape` — triggers an immediate background scrape
- `GET /api/status` — returns the timestamp and new-listing count from the last run
- `POST /api/save-link` — called by the Firefox extension to append a URL to `thrift-links.txt`

### 3. Database Layer — `thrift_tracker/db.py`
SQLite wrapper (file: `thrift_tracker.db`). Two tables:
- `listings` — stores each scraped listing (site, listing_id, title, size, price, image_url, listing_url, seen_at, reviewed flag)
- `runs` — logs each scrape run (start time, end time, new listing count)

Key functions: `init_db()`, `insert_listing()`, `get_new_listings()`, `mark_reviewed()`, `log_run()`, `get_last_run()`

### 4. Scrape Runner — `thrift_tracker/runner.py`
Orchestrates scraping across all configured searches. For each search entry in `config.json`, it:
- Resolves the correct scraper from the registry
- Calls `fetch_listings()` and inserts new items into the database
- Sends ntfy notifications on success, failure, or empty results (fails gracefully if ntfy-monitor is absent)

### 5. Scheduler — `thrift_tracker/scheduler.py`
Uses APScheduler's `BackgroundScheduler` with a `CronTrigger` to schedule `run_scrape()` automatically based on the `schedule` block in `config.json` (days of week, hour, minute — all in UTC).

### 6. Scrapers — `thrift_tracker/scraper/`
| File | Site | Notes |
|---|---|---|
| `base.py` | — | Abstract `BaseScraper` class; `fetch_listings()` must be implemented |
| `vinted.py` | Vinted | Playwright-based headless Chromium |
| `depop.py` | Depop | Playwright-based headless Chromium |
| `ebay.py` | eBay | Playwright-based headless Chromium |
| `poshmark.py` | Poshmark | May be blocked by login prompt |
| `__init__.py` | — | `SCRAPERS` dict maps site-name strings to scraper classes |

Each scraper returns a list of dicts with keys: `listing_id`, `title`, `size`, `price`, `image_url`, `listing_url`.

### 7. Frontend — `static/`
A single-page vanilla JS app (no framework):
- `index.html` — layout with header, status bar, listings grid, footer action bar
- `app.js` — fetches/renders listings, handles selection, opens tabs, marks reviewed, polls scrape status
- `style.css` — responsive CSS Grid layout with forest-green accent theme

### 8. Firefox Extension (`firefox-extension/`)
Adds a toolbar button that POSTs the current search URL to `/api/save-link`, appending it to `thrift-links.txt` for later import. Installed as a temporary add-on via `about:debugging`.

### 9. URL Importer — `import_links.py`
CLI utility to push URLs from `thrift-links.txt` (or a Firefox bookmarks HTML export) into `config.json`. Deduplicates and sorts by site.

---

## Step-by-Step: Running the Application

### Prerequisites
- Python 3.10+
- `pip` (or `py -m pip` on Windows)

### Step 1 — Install dependencies
```
py -m pip install -r requirements.txt
py -m playwright install chromium
```

### Step 2 — Create your config file
```
copy config.json.example config.json
```
Edit `config.json` to add your search URLs and preferred schedule.

### Step 3 — (Optional) Populate search URLs
Add URLs to `thrift-links.txt` (one per line), then import:
```
py import_links.py thrift-links.txt
```
Or convert a Firefox bookmarks export:
```
py import_links.py --convert bookmarks.html
py import_links.py thrift-links.txt
```

### Step 4 — Start the application
```
py run.py
```
To use a custom port, pass it as the first argument:
```
py run.py 5001
```

### Step 5 — Open the UI
Navigate to `http://127.0.0.1:<port>` in your browser.

### Step 6 — Use the UI
- **Run Scrape Now** — triggers an immediate scrape; the status bar polls until complete
- **Listings grid** — click a card to select it; multi-select is supported
- **Open Selected** — opens selected listings in new browser tabs
- **Mark Reviewed** — removes selected listings from the UI (sets `reviewed=1` in DB)

---

## Configuration Reference (`config.json`)

```json
{
  "searches": [
    { "label": "Levi 501 W28", "url": "https://...", "site": "vinted" }
  ],
  "schedule": {
    "days_of_week": ["tue", "fri"],
    "hour": 8,
    "minute": 0
  },
  "max_age_days": 30
}
```

- `schedule.hour` and `schedule.minute` are in **UTC**
- `max_age_days` hides listings older than this from the UI
