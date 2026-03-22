# BUILD_LOG.md

## Prompt 0 — Load Notifications Specification
**Status:** Completed with caveat
**Notes:** The file `SAR-notifications-pwa.md` was not found in the repository or system. Based on Prompt 8, the notification utility requires:
- `notify.success(message, project=...)` — called after a successful scrape run
- `notify.error(message, project=...)` — called when scrape fails with an exception
- `notify.manual_step(message, project=...)` — called when CAPTCHA/login wall detected

These three notification types (plus the project label context, the runner integration, and the sibling-repo path assumption) form the notification requirements woven into the build.

---

## Prompt 1 — Repository scaffold and dependencies
**Status:** Completed
**Commit:** `feat: initial repository scaffold`
**Notes:** Created full directory structure, requirements.txt, .gitignore, config.json.example, README.md, and all empty placeholder files.

---

## Prompt 2 — Database layer
**Status:** Completed
**Commit:** `feat: database layer`
**Notes:** Implemented thrift_tracker/db.py with sqlite3, init_db(), listing_exists(), insert_listing(), get_new_listings(), mark_reviewed(), log_run(), get_last_run(). Self-test passed: DB OK.

---

## Prompt 3 — Scraper base class
**Status:** Completed
**Commit:** `feat: scraper base class`
**Notes:** Implemented BaseScraper ABC with launch_browser() and safe_text() helpers. Playwright installed. Import verified OK.

---

## Prompt 4 — Vinted scraper
**Status:** Completed
**Commit:** `feat: Vinted scraper`
**Notes:** Implemented VintedScraper using [data-testid="regular-item-cell"] selector (verified 2025-01-01). Handles cookie consent, extracts listing_id from URL path, title/size/price/image from card elements. Import verified OK.

---

## Prompt 5 — Depop scraper
**Status:** Completed
**Commit:** `feat: Depop scraper`
**Notes:** Implemented DepopScraper. Uses li/article product card selectors (verified 2025-01-01). Handles cookie overlay, extracts path slug as listing_id. Import verified OK.

---

## Prompt 6 — eBay scraper
**Status:** Completed
**Commit:** `feat: eBay scraper`
**Notes:** Implemented EbayScraper using li.s-item selector (verified 2025-01-01). Strips "New Listing" prefix, skips "Shop on eBay" promoted placeholder, strips tracking query params. Import verified OK.

---

## Prompt 7 — Poshmark scraper
**Status:** Completed
**Commit:** `feat: Poshmark scraper`
**Notes:** Implemented PoshmarkScraper using div[data-et-name="listing"] selector (verified 2025-01-01). Detects login modal and returns [] with warning. Import verified OK.

---

## Prompt 8 — Scraper registry and run orchestration
**Status:** Completed
**Commit:** `feat: scraper registry, run orchestration, and ntfy notifications`
**Notes:** Implemented SCRAPERS dict in scraper/__init__.py. Implemented runner.py with run_scrape(). Ntfy notify calls wrapped with graceful fallback if ntfy-monitor is not present. Verified: SCRAPERS=['vinted', 'depop', 'ebay', 'poshmark'], Runner OK.

---

## Prompt 9 — Flask API
**Status:** Completed
**Commit:** `feat: Flask API`
**Notes:** Implemented all routes: GET /, GET /static/<path>, GET /api/listings, POST /api/listings/reviewed, POST /api/scrape, GET /api/status. Uses threading.Event to prevent concurrent scrapes. CORS header added via after_request. Verified: API OK.

---

## Prompt 10 — Scheduler
**Status:** Completed
**Commit:** `feat: scheduler`
**Notes:** Implemented BackgroundScheduler with CronTrigger in thrift_tracker/scheduler.py. Reads days_of_week/hour/minute from config. Verified: Scheduler OK.

---

## Prompt 11 — Entry point
**Status:** Completed
**Commit:** `feat: entry point`
**Notes:** Implemented run.py with config.json loading, db.init_db(), scheduler.start_scheduler(), startup banner, and Flask app.run(). Syntax verified OK.

---

## Prompt 12 — Frontend HTML
**Status:** Completed
**Commit:** `feat: frontend HTML`
**Notes:** Implemented static/index.html with header (title, Refresh, Run Scrape Now buttons), status bar, popup warning, listings container, empty state, sticky footer action bar, and script/style references.

---

## Prompt 13 — Frontend JavaScript
**Status:** Completed
**Commit:** `feat: frontend JavaScript`
**Notes:** Implemented static/app.js with state management, fetchListings(), renderListings(), updateFooter(), openSelected(), markReviewed(), runScrape(), fetchStatus(), polling, and DOMContentLoaded wiring. JS syntax verified OK.

---

## Prompt 14 — Stylesheet
**Status:** Completed
**Commit:** `feat: stylesheet`
**Notes:** Implemented static/style.css with full design spec: sticky header, grid layout, listing cards, selected state, action bar footer, responsive breakpoints, and all specified colors/typography.

---

## Prompt 15 — Integration checks and final polish
**Status:** Completed
**Commit:** `feat: integration checks, final polish, and README updates`
**Notes:**
- All four integration checks passed: DB OK, API OK, SCRAPERS=['vinted','depop','ebay','poshmark'], Runner OK.
- static/index.html references to app.js and style.css verified correct.
- All Python files have trailing newlines.
- README already had Known Limitations section from Prompt 1.
- No stray debug print() statements found.

---

## Session — Port Selection & Merge Bug (2026-Mar-22)
**Status:** Completed
**Notes:** Added optional CLI port selection to `run.py` (`py run.py 5001`, default 5000). After merging the PR into GitHub main, the feature silently failed: a second `port = config.get("port", 5000)` assignment from a pre-existing branch version survived the merge and overwrote the `sys.argv` value at runtime. Identified by inspecting the full file output; offending line removed. MRG updated. `PORT_SELECT.md` and `DEBUG_DIAGNOSIS_LESSONS.md` added to Claude Admin Docs.

---
