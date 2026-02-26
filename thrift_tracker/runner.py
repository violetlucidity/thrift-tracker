import sys
from datetime import datetime, timezone

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
    _success(f"{new_count} new listing(s) found.", project=_PROJECT)
    return new_count
