import re

from .base import BaseScraper

# Selector verified 2025-01-01 against depop.com search page.
# Product tiles are <li> elements wrapping <a> links inside the results grid.
# Historically also matched article[data-testid="product-card"].
CARD_SELECTOR = 'li[class*="styles__ProductCardContainer"], article[data-testid="product-card"], li:has(a[href*="/products/"])'
OVERLAY_SELECTOR = 'button[aria-label="Close"], button:has-text("Accept"), [data-testid="cookieBanner"] button'


class DepopScraper(BaseScraper):
    """Scraper for Depop search results."""

    def fetch_listings(self) -> list[dict]:
        pw, browser, page = None, None, None
        try:
            pw, browser, page = self.launch_browser()
            page.goto(self.config["url"], wait_until="domcontentloaded", timeout=30000)

            # Dismiss any cookie/age-gate overlay
            try:
                page.wait_for_selector(OVERLAY_SELECTOR, timeout=5000)
                page.click(OVERLAY_SELECTOR)
                page.wait_for_timeout(1000)
            except Exception:
                pass

            # Wait for product tiles to appear (React app — may take time)
            page.wait_for_selector(CARD_SELECTOR, timeout=10000)

            cards = page.query_selector_all(CARD_SELECTOR)[:48]
            listings = []
            for card in cards:
                try:
                    link_el = card.query_selector("a[href*='/products/']")
                    if not link_el:
                        continue
                    href = link_el.get_attribute("href") or ""
                    if not href.startswith("http"):
                        href = "https://www.depop.com" + href

                    # Use full path slug as listing_id
                    # e.g. /products/username-some-item-abc123/ -> "username-some-item-abc123"
                    match = re.search(r"/products/([^/?#]+)", href)
                    if not match:
                        continue
                    listing_id = match.group(1).rstrip("/")

                    title_el = card.query_selector('p[class*="title"], [class*="itemDescription"], [class*="productName"]')
                    title = self.safe_text(title_el) if title_el else None

                    size_el = card.query_selector('p[class*="size"], [class*="itemSize"]')
                    size = self.safe_text(size_el) if size_el else None

                    price_el = card.query_selector('p[class*="price"], [class*="itemPrice"]')
                    price = self.safe_text(price_el) if price_el else None

                    img_el = card.query_selector("img")
                    image_url = None
                    if img_el:
                        image_url = img_el.get_attribute("src") or img_el.get_attribute("data-src")

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
            print(f"[DepopScraper] ERROR: {e}")
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
