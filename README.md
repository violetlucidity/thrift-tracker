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
playwright install chromium
cp config.json.example config.json
# Edit config.json with your own search URLs and preferred schedule
python run.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Configuring config.json

For each saved search, paste the full URL from your browser address bar and set the `site` field to one of: `vinted`, `depop`, `ebay`, `poshmark`.

Example entry:
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
