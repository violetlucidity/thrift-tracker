#!/usr/bin/env python3
"""
import_links.py — Bulk-import search URLs into config.json

WORKFLOW
--------
  Option A — convert a Firefox bookmarks HTML export to thrift-links.txt,
             then import from that clean file:

      python import_links.py --convert bookmarks.html
      python import_links.py thrift-links.txt

  Option B — import a thrift-links.txt file you have built manually
             or that the Firefox extension has been appending to:

      python import_links.py thrift-links.txt
      py     import_links.py thrift-links.txt          # Windows

THRIFT-LINKS.TXT FORMAT
------------------------
  Plain URLs, one per line, grouped under [site] headings.
  [site] headings are optional — site is always auto-detected from the URL
  domain, so headings are just for human readability.

      [vinted]
      https://www.vinted.co.uk/catalog?search_text=levi+501

      [ebay]
      https://www.ebay.com/sch/i.html?_nkw=calvin+klein+sweater

  Lines starting with # and blank lines are ignored.
  Duplicate URLs (already in config.json) are skipped automatically.

CONFIG.JSON
-----------
  After import, entries in config.json are sorted by site:
  vinted → depop → ebay → poshmark.
"""

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# ---------------------------------------------------------------------------
# Site detection
# ---------------------------------------------------------------------------

DOMAIN_TO_SITE = {
    "vinted.co.uk": "vinted",
    "vinted.com": "vinted",
    "vinted.fr": "vinted",
    "vinted.de": "vinted",
    "vinted.nl": "vinted",
    "vinted.be": "vinted",
    "depop.com": "depop",
    "ebay.co.uk": "ebay",
    "ebay.com": "ebay",
    "ebay.de": "ebay",
    "ebay.fr": "ebay",
    "ebay.com.au": "ebay",
    "poshmark.com": "poshmark",
}

# Canonical display order in config.json
SITE_ORDER = ["vinted", "depop", "ebay", "poshmark"]
KNOWN_SITES = set(SITE_ORDER)


def detect_site(url: str) -> str | None:
    """Return site name inferred from the URL domain, or None."""
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return DOMAIN_TO_SITE.get(host)
    except Exception:
        return None


def auto_label(url: str, site: str) -> str:
    """Generate a readable label from a search URL when none is provided."""
    qs = parse_qs(urlparse(url).query)
    for param in ("search_text", "q", "query", "_nkw", "search_query", "keyword"):
        if param in qs:
            query = qs[param][0].replace("+", " ").replace("%20", " ")
            return f"{query.title()} ({site.title()})"
    path_tail = urlparse(url).path.rstrip("/").split("/")[-1]
    return f"{path_tail or site} ({site.title()})"


# ---------------------------------------------------------------------------
# thrift-links.txt parser
# ---------------------------------------------------------------------------

def parse_txt(path: Path) -> list[dict]:
    """Parse a thrift-links.txt file.

    Site is always determined by URL domain — [headings] are cosmetic only.
    """
    entries = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Skip [heading] lines — site comes from the URL
        if re.fullmatch(r"\[[^\]]*\]", line):
            continue

        # Support optional "url | label" syntax
        if "|" in line:
            url, _, label = line.partition("|")
            url = url.strip()
            label = label.strip()
        else:
            url = line
            label = ""

        if not url.startswith("http"):
            print(f"  Line {lineno}: not a URL, skipping: {url!r}", file=sys.stderr)
            continue

        site = detect_site(url)
        if not site:
            print(
                f"  Line {lineno}: unrecognised domain, skipping: {url!r}",
                file=sys.stderr,
            )
            continue

        entries.append({
            "label": label or auto_label(url, site),
            "url": url,
            "site": site,
        })
    return entries


# ---------------------------------------------------------------------------
# Firefox HTML bookmarks parser  →  thrift-links.txt
# ---------------------------------------------------------------------------

class _FirefoxParser(HTMLParser):
    """Extracts HREF attributes from a Firefox bookmarks HTML export."""

    def __init__(self):
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value and value.startswith("http"):
                    self.urls.append(value)


def convert_firefox_html(html_path: Path, out_path: Path):
    """Strip a Firefox bookmarks HTML file down to a clean thrift-links.txt.

    Only URLs whose domains match a known site are written.
    URLs are grouped under [site] headings, sorted by SITE_ORDER.
    """
    parser = _FirefoxParser()
    parser.feed(html_path.read_text(encoding="utf-8"))

    groups: dict[str, list[str]] = {site: [] for site in SITE_ORDER}
    skipped = 0
    for url in parser.urls:
        site = detect_site(url)
        if site:
            groups[site].append(url)
        else:
            skipped += 1

    total = sum(len(v) for v in groups.values())
    print(f"  Found {total} matching URL(s) ({skipped} skipped — unrecognised domain)")

    lines = [
        "# thrift-links.txt — generated from Firefox bookmarks export",
        "# Edit freely. Import with:  python import_links.py thrift-links.txt",
        "",
    ]
    for site in SITE_ORDER:
        if groups[site]:
            lines.append(f"[{site}]")
            lines.extend(groups[site])
            lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Written to {out_path}")


# ---------------------------------------------------------------------------
# thrift-links.txt append  (used by api.py save-link endpoint)
# ---------------------------------------------------------------------------

def append_to_thrift_links(links_path: Path, url: str, site: str) -> bool:
    """Append a URL to thrift-links.txt under the correct [site] heading.

    Returns True if written, False if the URL was already present.
    """
    text = links_path.read_text(encoding="utf-8") if links_path.exists() else ""

    # Duplicate check
    if url in text:
        return False

    lines = text.splitlines()

    heading = f"[{site}]"
    # Find the last line of the existing section for this site
    insert_after = None
    in_section = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == heading:
            in_section = True
            insert_after = i
        elif in_section:
            if stripped.startswith("http"):
                insert_after = i
            elif re.fullmatch(r"\[[^\]]*\]", stripped):
                # Hit the next section — stop
                break

    if insert_after is not None:
        # Insert URL after the last URL in the existing section
        lines.insert(insert_after + 1, url)
    else:
        # Section doesn't exist — append at end
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(heading)
        lines.append(url)
        lines.append("")

    links_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# config.json helpers
# ---------------------------------------------------------------------------

def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        sys.exit(
            f"ERROR: {config_path} not found.\n"
            "Run:  cp config.json.example config.json"
        )
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def sort_searches_by_site(searches: list[dict]) -> list[dict]:
    """Return searches sorted by site in SITE_ORDER, preserving relative order."""
    groups: dict[str, list[dict]] = {site: [] for site in SITE_ORDER}
    other: list[dict] = []
    for entry in searches:
        site = entry.get("site", "")
        if site in groups:
            groups[site].append(entry)
        else:
            other.append(entry)
    result = []
    for site in SITE_ORDER:
        result.extend(groups[site])
    result.extend(other)
    return result


def save_config(config: dict, config_path: Path):
    config["searches"] = sort_searches_by_site(config.get("searches", []))
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def merge_entries(config: dict, new_entries: list[dict]) -> tuple[int, int]:
    """Add new_entries to config['searches'], skipping URL duplicates."""
    existing_urls = {s["url"] for s in config.setdefault("searches", [])}
    added = skipped = 0
    for entry in new_entries:
        if entry["url"] in existing_urls:
            print(f"  SKIP  (already in config): {entry['url']}")
            skipped += 1
        else:
            config["searches"].append(entry)
            existing_urls.add(entry["url"])
            print(f"  ADD   [{entry['site']}] {entry['label']}")
            added += 1
    return added, skipped


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Import search URLs into config.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python import_links.py thrift-links.txt\n"
            "  py     import_links.py thrift-links.txt\n\n"
            "  # Convert a Firefox bookmarks HTML export first:\n"
            "  python import_links.py --convert bookmarks.html\n"
            "  python import_links.py thrift-links.txt\n"
        ),
    )
    ap.add_argument(
        "txt_file",
        nargs="?",
        default="thrift-links.txt",
        help="Path to thrift-links.txt (default: thrift-links.txt).",
    )
    ap.add_argument(
        "--convert",
        metavar="HTML_FILE",
        help=(
            "Convert a Firefox bookmarks HTML export to thrift-links.txt "
            "(strips all HTML cruft, keeps only URLs for known sites)."
        ),
    )
    ap.add_argument(
        "--output",
        metavar="PATH",
        default="thrift-links.txt",
        help="Output path for --convert (default: thrift-links.txt).",
    )
    ap.add_argument(
        "--config",
        default="config.json",
        metavar="PATH",
        help="Path to config.json (default: config.json).",
    )
    args = ap.parse_args()

    # --convert: Firefox HTML → thrift-links.txt
    if args.convert:
        html_path = Path(args.convert)
        if not html_path.exists():
            sys.exit(f"ERROR: File not found: {html_path}")
        out_path = Path(args.output)
        print(f"Converting {html_path} → {out_path}")
        convert_firefox_html(html_path, out_path)
        print("\nDone. Review thrift-links.txt, then run:")
        print(f"  python import_links.py {out_path}")
        return

    # Import from thrift-links.txt
    txt_path = Path(args.txt_file)
    if not txt_path.exists():
        sys.exit(
            f"ERROR: {txt_path} not found.\n"
            "Create it manually, run --convert on a Firefox export, or\n"
            "use the Thrift Tracker Firefox extension to populate it."
        )

    print(f"Parsing: {txt_path}")
    entries = parse_txt(txt_path)

    if not entries:
        print("No valid URLs found. Nothing to import.")
        return

    config_path = Path(args.config)
    config = load_config(config_path)

    print(f"\nFound {len(entries)} URL(s). Merging into {config_path}…\n")
    added, skipped = merge_entries(config, entries)
    save_config(config, config_path)
    print(f"\nDone — {added} added, {skipped} skipped (already present).")
    if added:
        print("Entries in config.json are now sorted: vinted → depop → ebay → poshmark.")


if __name__ == "__main__":
    main()
