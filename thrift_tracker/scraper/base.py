from abc import ABC, abstractmethod

from playwright.sync_api import sync_playwright


class BaseScraper(ABC):
    """Abstract base class for all site-specific scrapers."""

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(self, search_config: dict):
        self.config = search_config

    @abstractmethod
    def fetch_listings(self) -> list[dict]:
        """Fetch listings from the search URL.

        Each returned dict must contain at minimum:
            listing_id   str  — unique on that platform
            title        str
            size         str | None
            price        str | None  e.g. "£24.00"
            image_url    str | None
            listing_url  str  — absolute URL
        """
        ...

    def launch_browser(self) -> tuple:
        """Launch a headless Chromium browser and return (playwright, browser, page)."""
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(user_agent=self.USER_AGENT)
        page = context.new_page()
        return pw, browser, page

    def safe_text(self, locator) -> str | None:
        """Return inner_text() of a Playwright locator, or None on any exception."""
        try:
            return locator.inner_text()
        except Exception:
            return None
