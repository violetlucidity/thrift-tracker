import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = "thrift_tracker.db"


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn):
    """Add enrichment columns if they don't exist yet."""
    for col, typedef in [
        ("description", "TEXT"),
        ("brand",       "TEXT"),
        ("condition",   "TEXT"),
        ("enriched",    "INTEGER DEFAULT 0"),
    ]:
        try:
            conn.execute(f"ALTER TABLE listings ADD COLUMN {col} {typedef}")
        except Exception:
            pass  # column already exists


def init_db():
    """Create tables if they do not exist. Safe to call multiple times."""
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS listings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                site        TEXT NOT NULL,
                listing_id  TEXT NOT NULL,
                label       TEXT,
                title       TEXT,
                size        TEXT,
                price       TEXT,
                image_url   TEXT,
                listing_url TEXT NOT NULL,
                seen_at     TEXT,
                reviewed    INTEGER DEFAULT 0,
                UNIQUE (site, listing_id)
            );

            CREATE TABLE IF NOT EXISTS runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at  TEXT,
                finished_at TEXT,
                new_count   INTEGER
            );
        """)
        conn.commit()
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()


def listing_exists(site: str, listing_id: str) -> bool:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM listings WHERE site = ? AND listing_id = ?",
            (site, listing_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def insert_listing(data: dict) -> bool:
    """Insert a listing if not already present. Returns True if inserted."""
    conn = _get_conn()
    try:
        seen_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT OR IGNORE INTO listings
                (site, listing_id, label, title, size, price, image_url, listing_url, seen_at)
            VALUES
                (:site, :listing_id, :label, :title, :size, :price, :image_url, :listing_url, :seen_at)
            """,
            {**data, "seen_at": seen_at},
        )
        inserted = conn.execute("SELECT changes()").fetchone()[0]
        conn.commit()
        return inserted > 0
    finally:
        conn.close()


def get_new_listings(max_age_days: int = 30) -> list[dict]:
    """Return unreviewed listings seen within max_age_days, newest first."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    conn = _get_conn()
    try:
        rows = conn.execute(
            """
            SELECT * FROM listings
            WHERE reviewed = 0 AND seen_at >= ?
            ORDER BY seen_at DESC
            """,
            (cutoff,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def mark_reviewed(listing_ids: list[int]):
    """Set reviewed = 1 for the given row IDs."""
    if not listing_ids:
        return
    conn = _get_conn()
    try:
        placeholders = ",".join("?" for _ in listing_ids)
        conn.execute(
            f"UPDATE listings SET reviewed = 1 WHERE id IN ({placeholders})",
            listing_ids,
        )
        conn.commit()
    finally:
        conn.close()


def log_run(started_at: str, finished_at: str, new_count: int):
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO runs (started_at, finished_at, new_count) VALUES (?, ?, ?)",
            (started_at, finished_at, new_count),
        )
        conn.commit()
    finally:
        conn.close()


def get_last_run() -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_unenriched_listings(limit: int = 60) -> list[dict]:
    """Return up to `limit` listings where enriched = 0, oldest first."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM listings WHERE enriched = 0 ORDER BY id ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_enrichment(db_id: int, description: str | None,
                      brand: str | None, condition: str | None):
    """Set description, brand, condition and mark enriched=1 for a listing."""
    conn = _get_conn()
    try:
        conn.execute(
            """UPDATE listings
               SET description = ?, brand = ?, condition = ?, enriched = 1
               WHERE id = ?""",
            (description, brand, condition, db_id),
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    dummy = {
        "site": "vinted",
        "listing_id": "test_001",
        "label": "Test Search",
        "title": "Test Item",
        "size": "M",
        "price": "£10.00",
        "image_url": None,
        "listing_url": "https://example.com/items/test_001",
    }
    insert_listing(dummy)
    assert listing_exists("vinted", "test_001"), "listing_exists failed"
    print("DB OK")
