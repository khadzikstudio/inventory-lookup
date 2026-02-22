import os
import sqlite3
import numpy as np

DB_PATH = None

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path):
    global DB_PATH
    DB_PATH = db_path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            category    TEXT DEFAULT '',
            extra_data  TEXT DEFAULT '',
            image_file  TEXT DEFAULT '',
            thumb_file  TEXT DEFAULT '',
            embedding   BLOB
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
            name, category, extra_data,
            content='items',
            content_rowid='id'
        );

        CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
            INSERT INTO items_fts(rowid, name, category, extra_data)
            VALUES (new.id, new.name, new.category, new.extra_data);
        END;

        CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
            INSERT INTO items_fts(items_fts, rowid, name, category, extra_data)
            VALUES ('delete', old.id, old.name, old.category, old.extra_data);
        END;

        CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
            INSERT INTO items_fts(items_fts, rowid, name, category, extra_data)
            VALUES ('delete', old.id, old.name, old.category, old.extra_data);
            INSERT INTO items_fts(rowid, name, category, extra_data)
            VALUES (new.id, new.name, new.category, new.extra_data);
        END;
    """)
    conn.commit()
    conn.close()


def clear_items():
    conn = _connect()
    conn.execute("DELETE FROM items")
    conn.execute("DELETE FROM items_fts")
    conn.commit()
    conn.close()


def insert_item(name, category, extra_data, image_file, thumb_file, embedding_vector):
    emb_blob = None
    if embedding_vector is not None:
        emb_blob = np.array(embedding_vector, dtype=np.float32).tobytes()

    conn = _connect()
    cur = conn.execute(
        "INSERT INTO items (name, category, extra_data, image_file, thumb_file, embedding) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, category, extra_data, image_file, thumb_file, emb_blob),
    )
    item_id = cur.lastrowid
    conn.commit()
    conn.close()
    return item_id


def text_search(query, limit=60):
    """FTS5 search — returns list of (id, rank) tuples.
    Query can be pre-formatted with OR operators from expand_query."""
    conn = _connect()
    if " OR " in query:
        fts_query = query
    else:
        fts_query = " OR ".join(query.strip().split())
    try:
        rows = conn.execute(
            "SELECT rowid, rank FROM items_fts WHERE items_fts MATCH ? ORDER BY rank LIMIT ?",
            (fts_query, limit),
        ).fetchall()
    except Exception:
        fts_query = " OR ".join(query.strip().split())
        rows = conn.execute(
            "SELECT rowid, rank FROM items_fts WHERE items_fts MATCH ? ORDER BY rank LIMIT ?",
            (fts_query, limit),
        ).fetchall()
    conn.close()
    return [(r["rowid"], r["rank"]) for r in rows]


def get_all_embeddings():
    """Returns list of (id, numpy_vector) for items that have embeddings."""
    conn = _connect()
    rows = conn.execute(
        "SELECT id, embedding FROM items WHERE embedding IS NOT NULL"
    ).fetchall()
    conn.close()
    results = []
    for r in rows:
        vec = np.frombuffer(r["embedding"], dtype=np.float32)
        results.append((r["id"], vec))
    return results


def get_items_by_ids(ids):
    """Fetch full item rows for a list of IDs, preserving order."""
    if not ids:
        return []
    conn = _connect()
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT * FROM items WHERE id IN ({placeholders})", ids
    ).fetchall()
    conn.close()
    row_map = {r["id"]: dict(r) for r in rows}
    return [row_map[i] for i in ids if i in row_map]


def get_all_items(limit=2000, offset=0):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM items ORDER BY name LIMIT ? OFFSET ?", (limit, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_item_count():
    conn = _connect()
    count = conn.execute("SELECT COUNT(*) as c FROM items").fetchone()["c"]
    conn.close()
    return count


def get_categories():
    conn = _connect()
    rows = conn.execute(
        "SELECT DISTINCT category FROM items WHERE category != '' ORDER BY category"
    ).fetchall()
    conn.close()
    return [r["category"] for r in rows]
