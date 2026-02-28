#!/usr/bin/env python3
"""
import_links.py — Bulk-import search URLs into config.json

Usage:
    python import_links.py searches.txt
    py     import_links.py searches.txt                          # Windows

    python import_links.py searches.txt --config /path/to/config.json

    # Import from a Firefox bookmarks HTML export:
    python import_links.py --firefox ~/bookmarks.html
    python import_links.py --firefox ~/bookmarks.html --folder "Thrift Searches"

TXT format (see searches.txt.example):
    [site_name]                   start a section; site must be one of:
                                  vinted | depop | ebay | poshmark
    <url>                         one URL per line — label auto-generated
    <url> | <label>               URL with a custom label
    # comment                     ignored
    (blank lines ignored)

Firefox format:
    Export from Firefox → Library (Ctrl+Shift+B) →
    Import and Backup → Export Bookmarks to HTML.
    Pass the .html file with --firefox.
    Use --folder to limit import to one bookmark folder (recommended).
    Site is auto-detected from the URL domain.
"""

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# ---------------------------------------------------------------------------
# Site auto-detection from URL domain
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

KNOWN_SITES = {"vinted", "depop", "ebay", "poshmark"}


def detect_site(url: str) -> str | None:
    """Return site name inferred from the URL domain, or None."""
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return DOMAIN_TO_SITE.get(host)


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
# TXT file parser
# ---------------------------------------------------------------------------

def parse_txt(path: Path) -> list[dict]:
    """Parse a searches TXT file into a list of search-config dicts."""
    entries = []
    current_site = None

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        # Section heading: [site_name]
        m = re.fullmatch(r"\[([^\]]+)\]", line)
        if m:
            site = m.group(1).strip().lower()
            if site not in KNOWN_SITES:
                print(
                    f"  Line {lineno}: unknown site '{site}' "
                    f"(expected one of {sorted(KNOWN_SITES)}) — skipping section.",
                    file=sys.stderr,
                )
                current_site = None
            else:
                current_site = site
            continue

        if current_site is None:
            print(
                f"  Line {lineno}: URL found outside a [site] heading — skipping.",
                file=sys.stderr,
            )
            continue

        # URL line, optional label after pipe
        if "|" in line:
            url, _, label = line.partition("|")
            url = url.strip()
            label = label.strip() or auto_label(url, current_site)
        else:
            url = line
            label = auto_label(url, current_site)

        if not url.startswith("http"):
            print(f"  Line {lineno}: not a URL, skipping: {url!r}", file=sys.stderr)
            continue

        entries.append({"label": label, "url": url, "site": current_site})

    return entries


# ---------------------------------------------------------------------------
# Firefox HTML bookmarks parser
# ---------------------------------------------------------------------------

class _FirefoxParser(HTMLParser):
    """Minimal Firefox bookmarks HTML parser."""

    def __init__(self, folder_filter: str | None):
        super().__init__()
        self._folder_filter = folder_filter.lower().strip() if folder_filter else None
        self._in_target = self._folder_filter is None  # no filter → accept all
        self._depth = 0
        self._target_depth: int | None = None
        self._pending_folder: list[str] = []
        self._pending_href: str | None = None
        self._pending_title: list[str] = []
        self.entries: list[dict] = []

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "dl":
            self._depth += 1
        elif tag == "h3":
            self._pending_folder = []
        elif tag == "a":
            self._pending_href = attrs_d.get("href")
            self._pending_title = []

    def handle_endtag(self, tag):
        if tag == "dl":
            # Leaving the target folder depth → stop collecting
            if self._target_depth is not None and self._depth == self._target_depth:
                self._in_target = False
                self._target_depth = None
            self._depth -= 1
        elif tag == "h3":
            name = "".join(self._pending_folder).strip()
            if self._folder_filter and name.lower() == self._folder_filter:
                self._in_target = True
                self._target_depth = self._depth + 1  # the <dl> that follows
            self._pending_folder = []
        elif tag == "a":
            if self._in_target and self._pending_href:
                url = self._pending_href
                title = "".join(self._pending_title).strip()
                site = detect_site(url)
                if site:
                    self.entries.append(
                        {
                            "label": title or auto_label(url, site),
                            "url": url,
                            "site": site,
                        }
                    )
            self._pending_href = None
            self._pending_title = []

    def handle_data(self, data):
        if self._pending_href is not None:
            self._pending_title.append(data)
        elif self._pending_folder is not None:
            self._pending_folder.append(data)


def parse_firefox_html(path: Path, folder: str | None) -> list[dict]:
    """Parse a Firefox bookmarks HTML export file."""
    parser = _FirefoxParser(folder)
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.entries


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


def save_config(config: dict, config_path: Path):
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def merge_entries(config: dict, new_entries: list[dict]) -> tuple[int, int]:
    """Add new_entries to config['searches'], skipping exact URL duplicates."""
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
        description="Bulk-import search URLs into config.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python import_links.py searches.txt\n"
            "  py     import_links.py searches.txt\n\n"
            "  python import_links.py --firefox ~/bookmarks.html\n"
            "  python import_links.py --firefox ~/bookmarks.html --folder \"Thrift Searches\"\n"
        ),
    )
    ap.add_argument(
        "txt_file",
        nargs="?",
        help="Path to a searches TXT file (see searches.txt.example).",
    )
    ap.add_argument(
        "--firefox",
        metavar="HTML_FILE",
        help="Firefox bookmarks HTML export file.",
    )
    ap.add_argument(
        "--folder",
        metavar="FOLDER_NAME",
        help="Only import bookmarks from this Firefox folder (case-insensitive).",
    )
    ap.add_argument(
        "--config",
        default="config.json",
        metavar="PATH",
        help="Path to config.json (default: config.json).",
    )
    args = ap.parse_args()

    if not args.txt_file and not args.firefox:
        ap.error("Provide a TXT file or use --firefox <bookmarks.html>")

    config_path = Path(args.config)
    config = load_config(config_path)

    if args.firefox:
        ff_path = Path(args.firefox)
        if not ff_path.exists():
            sys.exit(f"ERROR: Firefox bookmarks file not found: {ff_path}")
        print(f"Parsing Firefox export: {ff_path}")
        if args.folder:
            print(f"  Folder filter: '{args.folder}'")
        entries = parse_firefox_html(ff_path, args.folder)
    else:
        txt_path = Path(args.txt_file)
        if not txt_path.exists():
            sys.exit(f"ERROR: File not found: {txt_path}")
        print(f"Parsing: {txt_path}")
        entries = parse_txt(txt_path)

    if not entries:
        print("No valid entries found. Nothing to import.")
        return

    print(f"\nFound {len(entries)} URL(s). Merging into {config_path}…\n")
    added, skipped = merge_entries(config, entries)
    save_config(config, config_path)
    print(f"\nDone — {added} added, {skipped} skipped (already present).")


if __name__ == "__main__":
    main()
