"""Filter engine for thrift tracker listings.

Provides URL filter hint parsing and listing filter application.
No external dependencies — standard library only.
"""

import re
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------------------
# URL filter hint parser
# ---------------------------------------------------------------------------

_STOP_WORDS = {"and", "or", "the", "with", "for", "in", "a", "an", "of", "to"}

_URL_PARAMS = {
    "vinted": {
        "size":      ["size_ids[]", "size_id"],
        "brand":     ["brand_ids[]", "brand_id"],
        "query":     ["search_text"],
        "condition": ["status[]", "status"],
    },
    "depop": {
        "size":      ["sizes[]", "size"],
        "brand":     ["brands[]", "brand"],
        "query":     ["q"],
        "condition": ["itemCondition[]", "itemCondition"],
    },
    "ebay": {
        "size":      [],
        "brand":     [],
        "query":     ["_nkw"],
        "condition": ["LH_ItemCondition"],
    },
    "poshmark": {
        "size":      ["size[]", "size"],
        "brand":     ["brand[]", "brand"],
        "query":     ["query"],
        "condition": ["condition[]", "condition"],
    },
}


def parse_url_filters(url: str, site: str) -> dict:
    """Parse a bookmark URL's query string for filter hints.

    Returns a dict with any of:
        size_hints, brand_hints, keyword_hints, condition_hints
    Keys with no detected values are omitted.
    """
    try:
        qs = parse_qs(urlparse(url).query, keep_blank_values=False)
    except Exception:
        return {}

    mapping = _URL_PARAMS.get(site, {})
    result = {}

    def _collect(key):
        vals = []
        for param in mapping.get(key, []):
            vals.extend(qs.get(param, []))
        return [v for v in vals if v]

    sizes = _collect("size")
    if sizes:
        result["size_hints"] = sizes

    brands = _collect("brand")
    if brands:
        result["brand_hints"] = brands

    conditions = _collect("condition")
    if conditions:
        result["condition_hints"] = conditions

    query_vals = _collect("query")
    if query_vals:
        raw = " ".join(query_vals)
        tokens = re.split(r"[\s+%20]+", raw)
        keywords = [t for t in tokens if t and t.lower() not in _STOP_WORDS and len(t) > 2]
        if keywords:
            result["keyword_hints"] = keywords

    return result


# ---------------------------------------------------------------------------
# Size normalisation
# ---------------------------------------------------------------------------

_SIZE_MAP = {
    "extra small": "xs", "xsmall": "xs",
    "small":       "s",
    "medium":      "m",
    "large":       "l",
    "extra large": "xl", "xlarge": "xl",
    "extra extra large": "xxl", "xxlarge": "xxl", "2xl": "xxl", "2 xl": "xxl",
}


def normalise_size(s: str | None) -> str | None:
    if not s:
        return None
    clean = s.strip().lower()
    if clean in _SIZE_MAP:
        return _SIZE_MAP[clean]
    # Already a short code like "xs", "s", "m", "l", "xl", "xxl"
    if clean in {"xs", "s", "m", "l", "xl", "xxl"}:
        return clean
    # Numeric e.g. "28", "28/30", "w28", "w28l30" — return lowercased
    return clean or None


# ---------------------------------------------------------------------------
# Price parsing
# ---------------------------------------------------------------------------

def _parse_price(price_str: str | None) -> float | None:
    if not price_str:
        return None
    # Strip currency symbols and whitespace
    cleaned = re.sub(r"[^\d.,]", "", price_str)
    if not cleaned:
        return None
    # Handle thousands separator: if comma appears before the last 3 digits
    # treat it as thousands sep; otherwise treat as decimal
    if "," in cleaned and "." in cleaned:
        # e.g. "1,234.56" — comma is thousands
        cleaned = cleaned.replace(",", "")
    elif cleaned.count(",") == 1:
        parts = cleaned.split(",")
        if len(parts[1]) <= 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Filter application
# ---------------------------------------------------------------------------

def apply_filters(listings: list[dict], rules: dict) -> list[dict]:
    """Filter listings list according to rules dict.

    Rules (all optional):
        keyword:    str   — words must appear in title or description
        sizes:      list  — normalised sizes to include
        brands:     list  — brand substrings to include (case-insensitive)
        conditions: list  — condition substrings to include (case-insensitive)
        price_max:  float — max price (inclusive)
        label:      str   — exact match on search label
    """
    keyword = rules.get("keyword", "").strip()
    sizes = [normalise_size(s) for s in rules.get("sizes", []) if s]
    brands = [b.lower() for b in rules.get("brands", []) if b]
    conditions = [c.lower() for c in rules.get("conditions", []) if c]
    price_max = rules.get("price_max")
    label = rules.get("label", "").strip()

    out = []
    for listing in listings:
        # --- keyword ---
        if keyword:
            words = [w for w in keyword.lower().split() if len(w) > 2]
            haystack = " ".join(filter(None, [
                listing.get("title") or "",
                listing.get("description") or "",
            ])).lower()
            if not all(w in haystack for w in words):
                continue

        # --- size ---
        if sizes:
            norm = normalise_size(listing.get("size"))
            if norm not in sizes:
                continue

        # --- brand ---
        if brands:
            listing_brand = (listing.get("brand") or "").lower()
            if not any(b in listing_brand for b in brands):
                continue

        # --- condition ---
        if conditions:
            listing_cond = (listing.get("condition") or "").lower()
            if not any(c in listing_cond for c in conditions):
                continue

        # --- price_max ---
        if price_max is not None:
            p = _parse_price(listing.get("price"))
            if p is None or p > price_max:
                continue

        # --- label ---
        if label:
            if listing.get("label", "") != label:
                continue

        out.append(listing)

    return out
