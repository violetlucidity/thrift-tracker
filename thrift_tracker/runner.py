import sys
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

sys.path.insert(0, "../ntfy-monitor")  # path to the ntfy-monitor sibling repo

try:
    import notify as _notify

    def _success(msg, project):
        _notify.success(msg, project=project)

    def _error(msg, project):
        _notify.error(msg, project=project)

    def _manual_step(msg, project):
        _notify.manual_step(msg, project=project)

except ImportError:
    def _success(msg, project):
        print(f"[notify] SUCCESS ({project}): {msg}")

    def _error(msg, project):
        print(f"[notify] ERROR ({project}): {msg}")

    def _manual_step(msg, project):
        print(f"[notify] MANUAL STEP ({project}): {msg}")

from thrift_tracker import db
from thrift_tracker.scraper import SCRAPERS
from thrift_tracker.scraper.detail import DETAIL_FETCHERS

_PROJECT = "Thrift Tracker"


def run_scrape(config: dict) -> int:
    """Run all configured scrapers and store new listings. Returns new_count."""
    db.init_db()
    started_at = datetime.now(timezone.utc).isoformat()
    new_count = 0

    try:
        for search in config.get("searches", []):
            site = search.get("site", "")
            label = search.get("label", "")

            scraper_cls = SCRAPERS.get(site)
            if scraper_cls is None:
                print(f'[runner] WARNING: Unknown site "{site}", skipping.')
                continue

            scraper = scraper_cls(search)
            listings = scraper.fetch_listings()

            if not listings:
                _manual_step(
                    f'Manual action required — check the scraper for "{label}" ({site}).',
                    project=_PROJECT,
                )

            n = 0
            for listing in listings:
                listing["site"] = site
                listing["label"] = label
                if db.insert_listing(listing):
                    n += 1
            new_count += n
            print(f'[{site}] "{label}" → {n} new listing(s)')

    except Exception as e:
        finished_at = datetime.now(timezone.utc).isoformat()
        db.log_run(started_at, finished_at, new_count)
        _error(f"Scrape failed: {str(e)}", project=_PROJECT)
        raise

    finished_at = datetime.now(timezone.utc).isoformat()
    db.log_run(started_at, finished_at, new_count)
    print(f"[runner] Run complete. {new_count} new listing(s) total.")

    try:
        enrich_new_listings()
    except Exception as e:
        print(f"[enricher] WARNING: enrichment step failed: {e}")

    _success(f"{new_count} new listing(s) found.", project=_PROJECT)
    return new_count


def enrich_new_listings() -> int:
    """Visit detail pages for unenriched listings. Returns count enriched."""
    pending = db.get_unenriched_listings(limit=60)
    if not pending:
        return 0

    # Group by site
    by_site: dict[str, list[dict]] = {}
    for listing in pending:
        by_site.setdefault(listing["site"], []).append(listing)

    _UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    total = 0
    for site, group in by_site.items():
        fetcher = DETAIL_FETCHERS.get(site)
        if fetcher is None:
            print(f"[enricher] No detail fetcher for site '{site}', skipping.")
            continue

        pw = None
        browser = None
        try:
            pw = sync_playwright().start()
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(user_agent=_UA)

            for i, listing in enumerate(group, 1):
                url = listing["listing_url"]
                print(f"[enricher] {site} {i}/{len(group)}: {url}")
                try:
                    data = fetcher(page, url)
                    db.update_enrichment(
                        listing["id"],
                        data.get("description"),
                        data.get("brand"),
                        data.get("condition"),
                    )
                    total += 1
                except Exception as e:
                    print(f"[enricher] {site} failed for {url}: {e}")
                    # Mark as enriched anyway to avoid retrying broken URLs
                    db.update_enrichment(listing["id"], None, None, None)
        except Exception as e:
            print(f"[enricher] {site} browser error: {e}")
        finally:
            try:
                if browser:
                    browser.close()
                if pw:
                    pw.stop()
            except Exception:
                pass

    print(f"[enricher] Enriched {total} listing(s).")
    return total
