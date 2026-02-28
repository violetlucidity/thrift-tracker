import re
from urllib.parse import urlparse

from .base import BaseScraper

# Selector verified 2025-01-01 against ebay.co.uk search results page.
# Result items are <li class="s-item"> elements.
CARD_SELECTOR = "li.s-item"


class EbayScraper(BaseScraper):
    """Scraper for eBay search results."""

    def fetch_listings(self) -> list[dict]:
        pw, browser, page = None, None, None
        try:
            pw, browser, page = self.launch_browser()
            page.goto(self.config["url"], wait_until="domcontentloaded", timeout=30000)

            page.wait_for_selector(CARD_SELECTOR, timeout=15000)

            cards = page.query_selector_all(CARD_SELECTOR)[:49]  # extra 1 to skip promoted placeholder
            listings = []
            for card in cards:
                try:
                    link_el = card.query_selector("a.s-item__link")
                    if not link_el:
                        continue
                    href = link_el.get_attribute("href") or ""

                    title_el = card.query_selector("span.s-item__title")
                    title = self.safe_text(title_el) if title_el else None

                    # Skip the promoted placeholder
                    if title and title.strip().lower() == "shop on ebay":
                        continue

                    # Strip "New Listing" prefix eBay adds to some titles
                    if title and title.startswith("New Listing"):
                        title = title[len("New Listing"):].strip()

                    # Extract eBay item number from URL path: /itm/123456789012
                    match = re.search(r"/itm/(\d+)", href)
                    if not match:
                        continue
                    listing_id = match.group(1)

                    # Strip tracking query parameters — keep path only up to item number
                    parsed = urlparse(href)
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

                    price_el = card.query_selector("span.s-item__price")
                    price = self.safe_text(price_el) if price_el else None

                    size_el = card.query_selector("span.s-item__dynamic, .s-item__subtitle")
                    size = self.safe_text(size_el) if size_el else None

                    img_el = card.query_selector("img")
                    image_url = None
                    if img_el:
                        src = img_el.get_attribute("src") or ""
                        # If src is a base64 placeholder, fall back to data-src
                        if src.startswith("data:"):
                            src = img_el.get_attribute("data-src") or src
                        image_url = src or None

                    listings.append({
                        "listing_id": listing_id,
                        "title": title,
                        "size": size,
                        "price": price,
                        "image_url": image_url,
                        "listing_url": clean_url,
                    })

                    if len(listings) >= 48:
                        break
                except Exception:
                    continue

            return listings

        except Exception as e:
            print(f"[EbayScraper] ERROR: {e}")
            return []
        finally:
            try:
                if page:
                    page.close()
                if browser:
                    browser.close()
                if pw:
                    pw.stop()
            except Exception:
                pass
