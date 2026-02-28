# Thrift Tracker

Thrift Tracker is a locally-run web application that periodically scrapes a user-defined list of secondhand clothing search URLs, stores new listings in a SQLite database, and presents them in a browser UI where you can review, check, and open listings for purchase.

## What It Does

- Scrapes bookmarked secondhand clothing searches (Vinted, Depop, eBay, Poshmark) twice a week (or on your configured schedule).
- Surfaces new listings in a local browser UI for manual review.
- Lets you open listings in tabs and mark them as reviewed.
- Sends notifications via ntfy when a scrape completes or fails.

## Setup

```bash
pip install -r requirements.txt
# Windows alternative:
py -m pip install -r requirements.txt

playwright install chromium
# Windows alternative:
py -m playwright install chromium

cp config.json.example config.json
# Edit config.json with your own search URLs and preferred schedule

python run.py
# Windows alternative:
py run.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

> **Note on `py`:** `py` is the [Python Launcher for Windows](https://docs.python.org/3/using/windows.html#launcher). On macOS/Linux use `python3` (or `python` if your environment defaults to Python 3).

## Configuring config.json

The recommended way to populate `config.json` is via `thrift-links.txt` and the importer — see below. You can also edit it directly; each entry needs a `label`, `url`, and `site`:

```json
{
  "label": "Levi 501 W28",
  "url": "https://www.vinted.co.uk/catalog?search_text=levi+501&size_ids[]=1234",
  "site": "vinted"
}
```

The `schedule` block controls when automatic scrapes run:
- `days_of_week`: list of 3-letter day abbreviations (e.g. `["tue", "fri"]`)
- `hour` and `minute`: time of day in UTC
- `max_age_days`: listings older than this are hidden from the UI

## Adding Search URLs

The cleanest workflow uses `thrift-links.txt` as a personal inbox and `import_links.py` to push those URLs into `config.json`. Site is always auto-detected from the URL domain — you never need to label it yourself.

### Option A — Firefox extension (one click per page)

Install the extension from the `firefox-extension/` folder (see [Firefox Extension](#firefox-extension) below). While Thrift Tracker is running, click the toolbar button on any search results page to save that URL directly to `thrift-links.txt`.

Then import whenever you're ready:

```bash
python import_links.py thrift-links.txt
py     import_links.py thrift-links.txt   # Windows
```

### Option B — Convert a Firefox bookmarks export

1. Press **Ctrl+Shift+B** → **Import and Backup → Export Bookmarks to HTML…**
2. Save the file (e.g. `bookmarks.html`).
3. Convert and strip all HTML cruft to a clean URL list:

```bash
python import_links.py --convert bookmarks.html
py     import_links.py --convert bookmarks.html   # Windows
```

This writes `thrift-links.txt` with only the URLs for known sites, grouped by site. Review it, then import:

```bash
python import_links.py thrift-links.txt
py     import_links.py thrift-links.txt   # Windows
```

### Option C — Edit thrift-links.txt manually

`thrift-links.txt` is a plain text file — one URL per line, with optional `[site]` headings for readability:

```
[vinted]
https://www.vinted.co.uk/catalog?search_text=levi+501

[ebay]
https://www.ebay.co.uk/sch/i.html?_nkw=levi+501+w28
```

Headings are cosmetic — site is always derived from the URL domain. After editing, run the importer as above.

Duplicates (URLs already in `config.json`) are skipped automatically. After each import `config.json` is re-sorted: vinted → depop → ebay → poshmark.

## Firefox Extension

The extension lets you save the URL of whatever search page you're looking at to `thrift-links.txt` with a single click — no copying, no switching windows.

### Install

1. Open Firefox and go to `about:debugging`.
2. Click **This Firefox** → **Load Temporary Add-on…**
3. Navigate to the `firefox-extension/` folder and select `manifest.json`.

The Thrift Tracker icon will appear in your toolbar.

> **Note:** "Temporary add-on" means it is unloaded when Firefox restarts. To make it permanent, package the folder as a `.zip` and sign it via [addons.mozilla.org](https://addons.mozilla.org/developers/), or use Firefox Developer Edition / Nightly with `xpinstall.signatures.required` set to `false` in `about:config`.

### Use

1. Make sure Thrift Tracker is running (`python run.py` / `py run.py`).
2. Navigate to a search results page on Vinted, Depop, eBay, or Poshmark.
3. Click the Thrift Tracker toolbar button.
4. The extension shows the detected site. Click **Save to thrift-links.txt**.
5. When you're ready to pull saved URLs into config.json:

```bash
python import_links.py thrift-links.txt
py     import_links.py thrift-links.txt   # Windows
```

## How the Scheduler Works

The app runs an APScheduler background job that triggers scrapes automatically on the configured days and time (in UTC). You can also trigger a scrape manually at any time using the **Run Scrape Now** button in the UI.

## Adding More Sites

Grailed, Mercari, Vestiaire Collective, ThredUp, and ASOS Marketplace are good candidates for additional scrapers.

A new scraper only requires:
1. Implementing the `BaseScraper` interface in `thrift_tracker/scraper/` (create a new file, e.g. `grailed.py`).
2. Registering it in `thrift_tracker/scraper/__init__.py` by adding it to the `SCRAPERS` dict.

## Known Limitations

- Scraper selectors may need updating if a site redesigns its frontend. Each scraper file contains a comment noting when its selectors were last verified.
- Poshmark may show a login prompt that blocks results; if this occurs the console will print a warning.
- Opening many tabs at once: the browser may block this; allow popups for localhost when prompted.
- All data is stored locally; nothing is sent to any external server.
- Schedule times are in UTC; adjust `hour` in `config.json` to match your local time.
- ntfy notifications require the `ntfy-monitor` repository to be present as a sibling directory. If it is not found, `run_scrape()` will raise an `ImportError` on first run. The path can be adjusted in `thrift_tracker/runner.py`.
