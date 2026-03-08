# Prompt A — Listing Detail Enrichment

## Goal
After each scrape, visit every newly-stored listing's own page to pull richer
data that the search-results grid does not reliably expose: full description,
brand, and condition. Store these in the database so the filter engine
(Prompt B) has accurate fields to work with.

---

## Step 1 — DB migration

In `thrift_tracker/db.py`:

1. Add a helper `_migrate()` called inside `init_db()` that runs the following
   ALTER TABLE statements. SQLite will raise an `OperationalError` if the
   column already exists; catch it silently so the function is safe to call
   multiple times:

   ```sql
   ALTER TABLE listings ADD COLUMN description TEXT;
   ALTER TABLE listings ADD COLUMN brand       TEXT;
   ALTER TABLE listings ADD COLUMN condition   TEXT;
   ALTER TABLE listings ADD COLUMN enriched    INTEGER DEFAULT 0;
   ```

2. Add two new module-level functions:

   ```python
   def get_unenriched_listings(limit: int = 60) -> list[dict]:
       """Return up to `limit` listings where enriched = 0, oldest first."""

   def update_enrichment(db_id: int, description: str | None,
                         brand: str | None, condition: str | None):
       """Set description, brand, condition, enriched=1 for a listing row."""
   ```

---

## Step 2 — Per-site detail scrapers

Create `thrift_tracker/scraper/detail.py`.

Each function receives a live Playwright `page` object and a `url` string.
It navigates to the URL, extracts the fields, and returns a dict:
`{"description": str|None, "brand": str|None, "condition": str|None}`.
All functions must catch exceptions and return `{"description": None,
"brand": None, "condition": None}` on failure.

### `fetch_vinted_detail(page, url) -> dict`
- Navigate to `url`.
- Description: try selector `[itemprop="description"]`, then
  `[class*="description"]`.
- Brand: look for a `<dt>` containing "Brand" or "Marque", then read the
  sibling `<dd>`. Also try `[class*="brand"] [class*="value"]`.
- Condition: same pattern but look for "Condition" / "État". Common Vinted
  values: "New with tags", "Good condition", "Satisfactory condition".
- Return the dict.

### `fetch_depop_detail(page, url) -> dict`
- Navigate to `url`.
- Description: `[class*="Description"]` or `p[class*="description"]`.
- Brand: `[class*="Brand"] [class*="value"]` or a `<span>` near a "Brand"
  label.
- Condition: look for "Condition" near the listing details section; common
  values: "New with tags", "Like new", "Good", "Fair", "Poor".
- Return the dict.

### `fetch_ebay_detail(page, url) -> dict`
- Navigate to `url`.
- eBay renders item specifics in a definition list or table. Try:
  `div.ux-layout-section--item-specifics`.
- Iterate over `<dt>`/`<dd>` pairs. Capture:
  - Brand: where `<dt>` text == "Brand"
  - Size: where `<dt>` text == "Size" (also update `size` if caller needs it,
    but this module only returns the three target fields)
  - Condition: read the `<div class="x-item-condition-text">` or the
    `<span class="ux-textspans">` inside the condition section at the top of
    the page.
- Description: `<div id="desc_div"> iframe` — note that eBay loads the
  description in an iframe. Use `page.frame_locator('#desc_ifr')` and then
  `locator('body')` to get text; fall back to `None` if not found within
  3 seconds.
- Return the dict.

### `fetch_poshmark_detail(page, url) -> dict`
- Navigate to `url`.
- Description: `[class*="listing__description"]` or `[data-et-name*="desc"]`.
- Brand: `[class*="listing__brand"]` or a `<a>` inside the brand row.
- Condition: look for "New with tags", "New without tags", "Very good",
  "Good", "Fair" near `[class*="condition"]` or the details section.
- Return the dict.

---

## Step 3 — Enrichment runner

In `thrift_tracker/runner.py`, add a new function `enrich_new_listings(config)`:

```python
def enrich_new_listings(config: dict) -> int:
    """Visit detail pages for unenriched listings. Returns count enriched."""
```

Implementation:
1. Call `db.get_unenriched_listings(limit=60)`.
2. If empty, return 0.
3. Group listings by `site`.
4. For each site group:
   - Import the matching detail fetcher from `thrift_tracker.scraper.detail`.
   - Use the `BaseScraper.launch_browser()` helper (instantiate a temporary
     `BaseScraper` subclass or call `sync_playwright` directly — prefer
     reusing `launch_browser` from any scraper for that site).
   - Actually, simpler: launch one playwright browser per site group using
     `sync_playwright` directly (don't use BaseScraper, just call
     `playwright.chromium.launch(headless=True)` with a realistic UA, create
     a page, then loop through each listing URL in that group calling the
     appropriate `fetch_*_detail(page, url)` function).
   - After each fetch, call `db.update_enrichment(listing["id"], ...)`.
   - Print `[enricher] {site} {i}/{n}: {listing_url}` for each.
   - Close browser when done with group.
5. Print `[enricher] Enriched {total} listing(s).`
6. Return total count.

Call `enrich_new_listings(config)` at the end of `run_scrape()`, after
`db.log_run(...)` and before the success notification. Wrap the call in a
try/except and print any error without re-raising, so enrichment failure does
not abort a successful scrape.

---

## Step 4 — Integration check

Run:
```bash
python -c "from thrift_tracker import db; db.init_db(); print('migration OK')"
python -c "from thrift_tracker.scraper.detail import fetch_vinted_detail; print('detail OK')"
python -c "from thrift_tracker.runner import enrich_new_listings; print('enricher OK')"
```

Fix any import errors before committing.

**Commit message:** `feat: per-listing detail enrichment (description, brand, condition)`
