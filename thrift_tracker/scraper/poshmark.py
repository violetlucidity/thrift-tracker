import re

from .base import BaseScraper

# Selector verified 2025-01-01 against poshmark.com search page.
# Listing tiles use div[data-et-name="listing"] historically; the results
# container also uses <div> with class containing "card".
CARD_SELECTOR = 'div[data-et-name="listing"], .cards-grid .card'
LOGIN_SELECTOR = '[data-test="login-modal"], .modal--login, form[action*="login"]'


class PoshmarkScraper(BaseScraper):
    """Scraper for Poshmark search results."""

    def fetch_listings(self) -> list[dict]:
        pw, browser, page = None, None, None
        try:
            pw, browser, page = self.launch_browser()
            page.goto(self.config["url"], wait_until="domcontentloaded", timeout=30000)

            # Check for login prompt / modal
            try:
                page.wait_for_selector(LOGIN_SELECTOR, timeout=3000)
                print("[PoshmarkScraper] WARNING: Login prompt may be blocking results.")
                return []
            except Exception:
                pass

            # Wait for listing cards
            page.wait_for_selector(CARD_SELECTOR, timeout=15000)

            cards = page.query_selector_all(CARD_SELECTOR)[:48]
            listings = []
            for card in cards:
                try:
                    link_el = card.query_selector("a[href]")
                    if not link_el:
                        continue
                    href = link_el.get_attribute("href") or ""
                    if not href.startswith("http"):
                        href = "https://poshmark.com" + href

                    # listing_id = alphanumeric slug at end of path
                    match = re.search(r"/listing/([^/?#]+)", href)
                    if not match:
                        # fall back to last path segment
                        segments = href.rstrip("/").split("/")
                        listing_id = segments[-1] if segments else None
                    else:
                        listing_id = match.group(1)

                    if not listing_id:
                        continue

                    title_el = card.query_selector('[class*="title"], [class*="listing__title"], a span')
                    title = self.safe_text(title_el) if title_el else None

                    size_el = card.query_selector('[class*="size"], [class*="listing__size"]')
                    size = self.safe_text(size_el) if size_el else None

                    price_el = card.query_selector('[class*="price"], [class*="listing__price"]')
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
            print(f"[PoshmarkScraper] ERROR: {e}")
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
