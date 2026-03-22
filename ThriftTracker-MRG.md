# ThriftTracker Machine Reference Guide (MRG)
**Last updated:** 2026Mar22-1430

> Token-efficient reference. Read this instead of source files where possible.

---

## Entry Point: `run.py`
- Loads `config.json` → exits with message if missing
- Optional CLI port arg: `py run.py 5001` (default 5000 if omitted or invalid)
- Calls `db.init_db()`, `scheduler.start_scheduler(config)`
- Prints startup banner with resolved URL, then calls `app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)`

## Flask API: `thrift_tracker/api.py`
| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Serve `static/index.html` |
| `/static/<path>` | GET | Serve static assets |
| `/api/listings` | GET | Unreviewed listings; param: `max_age_days` |
| `/api/listings/reviewed` | POST | Body: `{"ids": [1,2,3]}` |
| `/api/scrape` | POST | Trigger background scrape (threading.Event) |
| `/api/status` | GET | `{last_run, new_count}` |
| `/api/save-link` | POST | Append URL to `thrift-links.txt` |

- CORS: `Access-Control-Allow-Origin: *` on all responses
- Config loaded at module import time from `config.json`

## Database: `thrift_tracker/db.py`
- File: `thrift_tracker.db` (SQLite)
- Table `listings`: `id, site, listing_id, label, title, size, price, image_url, listing_url, seen_at, reviewed`
- Table `runs`: `id, started_at, finished_at, new_count`
- Key functions:
  - `init_db()` — creates tables
  - `listing_exists(site, listing_id) → bool`
  - `insert_listing(data: dict) → bool` — returns True if new
  - `get_new_listings(max_age_days=30) → list[dict]`
  - `mark_reviewed(ids: list[int])`
  - `log_run(started_at, finished_at, new_count)`
  - `get_last_run() → dict | None`

## Runner: `thrift_tracker/runner.py`
- `run_scrape(config: dict) → int` (returns new count)
- Iterates `config["searches"]`; resolves scraper via `SCRAPERS[entry["site"]]`
- Calls `scraper.fetch_listings()` → inserts new listings
- ntfy notifications via sibling `ntfy-monitor/` repo (graceful fallback if absent)

## Scheduler: `thrift_tracker/scheduler.py`
- `start_scheduler(config)` — BackgroundScheduler + CronTrigger
- Reads `config["schedule"]`: `days_of_week`, `hour`, `minute` (UTC)
- Schedules `runner.run_scrape(config)`

## Scrapers: `thrift_tracker/scraper/`
- `__init__.py`: `SCRAPERS = {"vinted": VintedScraper, "depop": DepopScraper, "ebay": EbayScraper, "poshmark": PoshmarkScraper}`
- `base.py`: `BaseScraper` ABC; `fetch_listings() → list[dict]`; helpers: `launch_browser()`, `safe_text(locator)`
- Each scraper returns dicts with: `listing_id, title, size, price, image_url, listing_url`
- Browser: headless Chromium via Playwright; UA: Chrome 124 / Windows

## Frontend: `static/`
- `index.html`: sticky header (Refresh, Run Scrape), status bar, listings grid, sticky footer (Open Selected, Mark Reviewed)
- `app.js`: state = `listings[]`, `selected Set`; polls `/api/status` every 5s during scrape
- `style.css`: CSS Grid `repeat(auto-fill, minmax(240px, 1fr))`; accent `#2d6a4f` (forest green)

## Config: `config.json`
```json
{
  "searches": [{"label":"...", "url":"...", "site":"vinted|depop|ebay|poshmark"}],
  "schedule": {"days_of_week":["tue","fri"], "hour":8, "minute":0},
  "max_age_days": 30
}
```

## Key Files at a Glance
| File | Purpose |
|---|---|
| `run.py` | Start app; optional port arg |
| `thrift_tracker/api.py` | Flask routes |
| `thrift_tracker/db.py` | SQLite layer |
| `thrift_tracker/runner.py` | Scrape orchestration |
| `thrift_tracker/scheduler.py` | Cron scheduling |
| `thrift_tracker/scraper/__init__.py` | Scraper registry |
| `thrift_tracker/scraper/base.py` | Abstract base class |
| `config.json` | User config (gitignored) |
| `config.json.example` | Template |
| `import_links.py` | URL importer CLI |
| `static/index.html` | Frontend shell |
| `static/app.js` | Frontend logic |
| `static/style.css` | Styles |

## Dependencies (`requirements.txt`)
- `flask>=3.0`
- `playwright>=1.44`
- `apscheduler>=3.10`
- `python-dotenv>=1.0`
