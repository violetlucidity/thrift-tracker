# Prompt B — Filter Engine

Depends on Prompt A. Assumes `description`, `brand`, `condition`, `enriched`
columns exist in the `listings` table.

## Goal
Let the user filter the listings grid by keyword, size, brand, condition, and
price without re-running a scrape. Filters are applied server-side. The UI
exposes a collapsible filter bar populated from the live data.

---

## Step 1 — `thrift_tracker/filters.py`

Create this new module. It has no imports beyond the standard library.

### `parse_url_filters(url: str, site: str) -> dict`

Parse the bookmark URL's query string to extract intended filter hints.
Return a dict with any of these keys present (omit keys with no value found):

```python
{
    "size_hints":      list[str],   # e.g. ["M", "Medium", "28"]
    "brand_hints":     list[str],   # e.g. ["Levi's", "Carhartt"]
    "keyword_hints":   list[str],   # words from the search query
    "condition_hints": list[str],   # e.g. ["new", "good"]
}
```

Site-specific param mappings (use `urllib.parse.parse_qs`):

| site      | size params                    | brand params              | query param   | condition param |
|-----------|-------------------------------|---------------------------|---------------|-----------------|
| vinted    | `size_ids[]`, `size_id`        | `brand_ids[]`, `brand_id` | `search_text` | `status[]`      |
| depop     | `sizes[]`, `size`              | `brands[]`, `brand`       | `q`           | `itemCondition[]` |
| ebay      | (none reliable)                | (none reliable)           | `_nkw`        | `LH_ItemCondition` |
| poshmark  | `size[]`                       | `brand[]`                 | `query`       | `condition[]`   |

For the keyword param, split on `+`, `%20`, and spaces; strip common stop
words ("and", "or", "the", "with"); return remaining tokens as `keyword_hints`.

For size/brand/condition params, return the raw values as-is (the filter
engine will handle fuzzy matching).

### `normalise_size(s: str | None) -> str | None`

Lowercase, strip whitespace, expand common abbreviations:
- "xs" / "extra small" → "xs"
- "s" / "small" → "s"
- "m" / "medium" → "m"
- "l" / "large" → "l"
- "xl" / "extra large" → "xl"
- "xxl" / "2xl" → "xxl"
- Numeric waist/length strings (e.g. "28", "28/30", "w28", "w28l30") → keep as-is lowercased.
- Return `None` if input is `None` or empty.

### `apply_filters(listings: list[dict], rules: dict) -> list[dict]`

`rules` keys (all optional):
- `keyword: str` — filter: all words in keyword must appear in
  `title` OR `description` (case-insensitive). Short (≤2 char) words skip.
- `sizes: list[str]` — filter: `normalise_size(listing["size"])` must be in
  the normalised rule sizes. Empty list = no filter.
- `brands: list[str]` — filter: `listing["brand"]` contains any of the brand
  strings (case-insensitive). Empty list = no filter.
- `conditions: list[str]` — filter: `listing["condition"]` contains any of
  the condition strings (case-insensitive). Empty list = no filter.
- `price_max: float | None` — filter: parse the price string by stripping
  non-numeric chars except `.` and `,`; treat `,` as thousands separator;
  keep listing if parsed price ≤ price_max. Skip listing if price unparseable.
- `label: str | None` — exact match against `listing["label"]`. Empty = no filter.

Apply filters conjunctively (AND). Return filtered list preserving order.

---

## Step 2 — Update `thrift_tracker/api.py`

Update the `/api/listings` route to accept and apply filter params:

```python
@app.route("/api/listings")
def get_listings():
    max_age_days = int(request.args.get("max_age_days", config.get("max_age_days", 30)))
    listings = db.get_new_listings(max_age_days=max_age_days)

    from thrift_tracker.filters import apply_filters
    rules = {}
    if kw := request.args.get("keyword", "").strip():
        rules["keyword"] = kw
    if sz := request.args.get("sizes", "").strip():
        rules["sizes"] = [s.strip() for s in sz.split(",") if s.strip()]
    if br := request.args.get("brands", "").strip():
        rules["brands"] = [b.strip() for b in br.split(",") if b.strip()]
    if co := request.args.get("conditions", "").strip():
        rules["conditions"] = [c.strip() for c in co.split(",") if c.strip()]
    if pm := request.args.get("price_max", "").strip():
        try:
            rules["price_max"] = float(pm)
        except ValueError:
            pass
    if lb := request.args.get("label", "").strip():
        rules["label"] = lb

    if rules:
        listings = apply_filters(listings, rules)

    return jsonify(listings)
```

Also add a new route `GET /api/filter-options` that returns the distinct
non-null values currently in the unreviewed listings, for populating UI
dropdowns:

```python
@app.route("/api/filter-options")
def filter_options():
    listings = db.get_new_listings(max_age_days=config.get("max_age_days", 30))
    sizes  = sorted({l["size"]      for l in listings if l.get("size")})
    brands = sorted({l["brand"]     for l in listings if l.get("brand")})
    conds  = sorted({l["condition"] for l in listings if l.get("condition")})
    labels = sorted({l["label"]     for l in listings if l.get("label")})
    return jsonify({"sizes": sizes, "brands": brands,
                    "conditions": conds, "labels": labels})
```

---

## Step 3 — Update `static/index.html`

Add a `<div id="filter-bar">` immediately after `<div id="status-bar">`:

```html
<div id="filter-bar">
  <input  id="f-keyword"   type="search"  placeholder="Search titles & descriptions…" />
  <select id="f-label"     multiple><option value="">All searches</option></select>
  <select id="f-size"      multiple><option value="">All sizes</option></select>
  <select id="f-brand"     multiple><option value="">All brands</option></select>
  <select id="f-condition" multiple><option value="">All conditions</option></select>
  <input  id="f-price-max" type="number"  placeholder="Max price" min="0" step="0.01" />
  <button class="btn-secondary" id="btn-clear-filters">Clear</button>
  <span   id="filter-count"></span>
</div>
```

---

## Step 4 — Update `static/app.js`

### New state
```js
let filterDebounce = null;
```

### `fetchFilterOptions()`
- `GET /api/filter-options`
- For each of `sizes`, `brands`, `conditions`, `labels`: populate the
  matching `<select>` with `<option value="{v}">{v}</option>` elements,
  appending to (not replacing) the existing "All …" option.

### Update `fetchListings()`
Read the current filter control values and build a query string:
- `keyword`: value of `#f-keyword`
- `sizes`: selected options from `#f-size` (joined with `,`)
- `brands`: selected options from `#f-brand` (joined with `,`)
- `conditions`: selected options from `#f-condition` (joined with `,`)
- `price_max`: value of `#f-price-max`
- `label`: selected options from `#f-label` (joined with `,`)

Append non-empty params to the fetch URL: `/api/listings?keyword=…&sizes=…`

After receiving listings, update `#filter-count` with:
- `"{n} listing(s)"` if no filters active
- `"{n} listing(s) matching filters"` if any filter is active

### Wire up filter controls
In `DOMContentLoaded`:
- `#f-keyword`: on `input`, debounce 300 ms then call `fetchListings()`.
- `#f-size`, `#f-brand`, `#f-condition`, `#f-label`: on `change`, call
  `fetchListings()` immediately.
- `#f-price-max`: on `input`, debounce 500 ms then call `fetchListings()`.
- `#btn-clear-filters`: on `click`, reset all filter controls to their
  default state, then call `fetchListings()`.

Call `fetchFilterOptions()` in `DOMContentLoaded` after `fetchListings()`.

---

## Step 5 — Update `static/style.css`

Add styles for the filter bar:

```css
#filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.6rem 1rem;
  border-bottom: 1px solid #e0e0e0;
  background: #f9fbfa;
  align-items: center;
}

#filter-bar input[type="search"],
#filter-bar input[type="number"] {
  padding: 0.3rem 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.85rem;
}

#filter-bar input[type="search"] { min-width: 200px; }
#filter-bar input[type="number"] { width: 90px; }

#filter-bar select {
  padding: 0.3rem 0.4rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.85rem;
  min-width: 110px;
  max-height: 80px;
}

#filter-count {
  font-size: 0.8rem;
  color: #666;
  margin-left: auto;
}

@media (max-width: 600px) {
  #filter-bar { flex-direction: column; align-items: stretch; }
  #filter-bar input[type="search"] { min-width: unset; width: 100%; }
  #filter-count { margin-left: 0; }
}
```

---

## Step 6 — Integration check

Run:
```bash
python -c "from thrift_tracker.filters import apply_filters, parse_url_filters; print('filters OK')"
python -c "from thrift_tracker.api import app; print('API OK')"
```

Verify `static/index.html` references to filter IDs are consistent with
`app.js`.

**Commit message:** `feat: filter engine — keyword, size, brand, condition, price filters + filter bar UI`
