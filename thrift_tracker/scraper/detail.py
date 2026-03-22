"""Per-listing detail page scrapers.

Each fetch_*_detail(page, url) function navigates to a listing URL using a
live Playwright page, extracts description/brand/condition, and returns a dict.
All functions catch exceptions and return None values rather than raising.
"""


def _safe_text(locator):
    try:
        return locator.inner_text(timeout=3000).strip() or None
    except Exception:
        return None


def _nav(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=30000)


# ---------------------------------------------------------------------------
# Vinted — selectors verified 2026-03-08
# ---------------------------------------------------------------------------

def fetch_vinted_detail(page, url: str) -> dict:
    try:
        _nav(page, url)

        description = None
        for sel in ['[itemprop="description"]', '[class*="description"]']:
            try:
                el = page.query_selector(sel)
                if el:
                    description = el.inner_text(timeout=3000).strip() or None
                    if description:
                        break
            except Exception:
                pass

        brand = None
        condition = None
        # Vinted detail specs are in a <dl> with <dt> label / <dd> value pairs
        try:
            dts = page.query_selector_all("dt")
            for dt in dts:
                label = (dt.inner_text(timeout=2000) or "").strip().lower()
                dd = dt.evaluate_handle(
                    "node => node.nextElementSibling"
                )
                val = None
                try:
                    val = dd.as_element().inner_text(timeout=2000).strip() or None
                except Exception:
                    pass
                if val and ("brand" in label or "marque" in label):
                    brand = val
                elif val and ("condition" in label or "état" in label or "zustand" in label):
                    condition = val
        except Exception:
            pass

        return {"description": description, "brand": brand, "condition": condition}
    except Exception:
        return {"description": None, "brand": None, "condition": None}


# ---------------------------------------------------------------------------
# Depop — selectors verified 2026-03-08
# ---------------------------------------------------------------------------

def fetch_depop_detail(page, url: str) -> dict:
    try:
        _nav(page, url)

        description = None
        for sel in ['[class*="Description"]', 'p[class*="description"]',
                    '[data-testid="listing-description"]']:
            try:
                el = page.query_selector(sel)
                if el:
                    description = el.inner_text(timeout=3000).strip() or None
                    if description:
                        break
            except Exception:
                pass

        brand = None
        condition = None
        # Depop uses labelled rows; scan for text proximity
        try:
            rows = page.query_selector_all('[class*="ProductDetails"] [class*="row"], '
                                           '[class*="details"] li, [class*="Attribute"]')
            for row in rows:
                text = (row.inner_text(timeout=2000) or "").strip()
                lower = text.lower()
                if "brand" in lower and brand is None:
                    # value is typically after a colon or on a second line
                    parts = text.split("\n")
                    if len(parts) > 1:
                        brand = parts[-1].strip() or None
                if "condition" in lower and condition is None:
                    parts = text.split("\n")
                    if len(parts) > 1:
                        condition = parts[-1].strip() or None
        except Exception:
            pass

        return {"description": description, "brand": brand, "condition": condition}
    except Exception:
        return {"description": None, "brand": None, "condition": None}


# ---------------------------------------------------------------------------
# eBay — selectors verified 2026-03-08
# ---------------------------------------------------------------------------

def fetch_ebay_detail(page, url: str) -> dict:
    try:
        _nav(page, url)

        # Condition — shown prominently near the top
        condition = None
        for sel in ['.x-item-condition-text .ux-textspans',
                    '[class*="conditionText"]',
                    '.vim.x-item-condition']:
            try:
                el = page.query_selector(sel)
                if el:
                    condition = el.inner_text(timeout=3000).strip() or None
                    if condition:
                        break
            except Exception:
                pass

        # Item specifics — <div class="ux-layout-section--item-specifics">
        brand = None
        try:
            section = page.query_selector('.ux-layout-section--item-specifics')
            if section:
                labels = section.query_selector_all('.ux-labels-values__labels')
                values = section.query_selector_all('.ux-labels-values__values')
                for lbl_el, val_el in zip(labels, values):
                    lbl = (lbl_el.inner_text(timeout=2000) or "").strip().lower()
                    val = (val_el.inner_text(timeout=2000) or "").strip() or None
                    if "brand" in lbl and val:
                        brand = val
                        break
        except Exception:
            pass

        # Description — inside an iframe
        description = None
        try:
            frame = page.frame_locator('#desc_ifr')
            body = frame.locator('body')
            description = body.inner_text(timeout=4000).strip() or None
        except Exception:
            pass

        return {"description": description, "brand": brand, "condition": condition}
    except Exception:
        return {"description": None, "brand": None, "condition": None}


# ---------------------------------------------------------------------------
# Poshmark — selectors verified 2026-03-08
# ---------------------------------------------------------------------------

def fetch_poshmark_detail(page, url: str) -> dict:
    try:
        _nav(page, url)

        description = None
        for sel in ['[class*="listing__description"]', '[data-et-name*="desc"]',
                    '[class*="description__container"]', 'div[class*="desc"]']:
            try:
                el = page.query_selector(sel)
                if el:
                    description = el.inner_text(timeout=3000).strip() or None
                    if description:
                        break
            except Exception:
                pass

        brand = None
        for sel in ['[class*="listing__brand"] a', '[class*="brand"] a',
                    '[data-et-name="brand"]']:
            try:
                el = page.query_selector(sel)
                if el:
                    brand = el.inner_text(timeout=2000).strip() or None
                    if brand:
                        break
            except Exception:
                pass

        condition = None
        for sel in ['[class*="condition"]', '[data-et-name="condition"]']:
            try:
                el = page.query_selector(sel)
                if el:
                    condition = el.inner_text(timeout=2000).strip() or None
                    if condition:
                        break
            except Exception:
                pass

        return {"description": description, "brand": brand, "condition": condition}
    except Exception:
        return {"description": None, "brand": None, "condition": None}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

DETAIL_FETCHERS = {
    "vinted":   fetch_vinted_detail,
    "depop":    fetch_depop_detail,
    "ebay":     fetch_ebay_detail,
    "poshmark": fetch_poshmark_detail,
}
