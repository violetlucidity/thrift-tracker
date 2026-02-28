import re

from .base import BaseScraper

# Selector verified 2025-01-01 against vinted.co.uk catalog page.
# Listing cards are <div> elements with data-testid="regular-item-cell",
# each containing an <a> link to the item.
CARD_SELECTOR = '[data-testid="regular-item-cell"]'
CONSENT_SELECTOR = '[data-testid="cookie-accept-button"], button:has-text("Accept"), button:has-text("I agree")'


class VintedScraper(BaseScraper):
    """Scraper for Vinted search results."""

    def fetch_listings(self) -> list[dict]:
        pw, browser, page = None, None, None
        try:
            pw, browser, page = self.launch_browser()
            page.goto(self.config["url"], wait_until="domcontentloaded", timeout=30000)

            # Handle cookie consent banner if present
            try:
                page.wait_for_selector(CONSENT_SELECTOR, timeout=5000)
                page.click(CONSENT_SELECTOR)
                page.wait_for_timeout(1000)
            except Exception:
                pass

            # Wait for listing cards
            page.wait_for_selector(CARD_SELECTOR, timeout=15000)

            cards = page.query_selector_all(CARD_SELECTOR)[:48]
            listings = []
            for card in cards:
                try:
                    link_el = card.query_selector("a[href*='/items/']")
                    if not link_el:
                        continue
                    href = link_el.get_attribute("href") or ""
                    if not href.startswith("http"):
                        href = "https://www.vinted.co.uk" + href

                    # Extract numeric ID from path: /items/1234567890-title
                    match = re.search(r"/items/(\d+)", href)
                    if not match:
                        continue
                    listing_id = match.group(1)

                    title_el = card.query_selector('[data-testid="description-title"], .ItemBox__title, h3')
                    title = self.safe_text(title_el) if title_el else None

                    size_el = card.query_selector('[data-testid="item-size"], .ItemBox__size')
                    size = self.safe_text(size_el) if size_el else None

                    price_el = card.query_selector('[data-testid="item-price"], .ItemBox__price, [class*="price"]')
                    price = self.safe_text(price_el) if price_el else None

                    img_el = card.query_selector("img")
                    image_url = img_el.get_attribute("src") if img_el else None

                    listings.append({
                        "listing_id": listing_id,
                        "title": title,
                        "size": size,
                        "price": price,
                        "image_url": image_url,
                        "listing_url": href,
                    })
                except Exception:
                    continue

            return listings

        except Exception as e:
            print(f"[VintedScraper] ERROR: {e}")
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
