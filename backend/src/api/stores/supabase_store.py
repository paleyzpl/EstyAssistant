"""Supabase Postgres-backed credential and job store.

Requires SUPABASE_DB_URL env var, e.g.:
  postgresql://postgres.xxx:[email protected]:5432/postgres

Schema auto-created on first use. See SCHEMA_SQL below.
"""

import json
import logging
import os
import time
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

DB_URL = os.environ.get("SUPABASE_DB_URL", "")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS kv_store (
    pk TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
    updated_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
    ttl BIGINT
);

CREATE INDEX IF NOT EXISTS idx_kv_store_created ON kv_store (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_kv_store_ttl ON kv_store (ttl) WHERE ttl IS NOT NULL;
"""

_initialized = False


@contextmanager
def _conn():
    """Get a database connection."""
    if not DB_URL:
        raise ValueError("SUPABASE_DB_URL is not set")
    conn = psycopg.connect(DB_URL, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_schema():
    global _initialized
    if _initialized:
        return
    with _conn() as c:
        with c.cursor() as cur:
            cur.execute(SCHEMA_SQL)
    _initialized = True
    logger.info("Supabase schema initialized")


def _put(pk: str, data: dict, ttl_seconds: int | None = None):
    _ensure_schema()
    ttl = int(time.time()) + ttl_seconds if ttl_seconds else None
    with _conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """
                INSERT INTO kv_store (pk, data, ttl, updated_at)
                VALUES (%s, %s, %s, EXTRACT(EPOCH FROM NOW())::BIGINT)
                ON CONFLICT (pk) DO UPDATE SET
                    data = EXCLUDED.data,
                    ttl = EXCLUDED.ttl,
                    updated_at = EXCLUDED.updated_at
                """,
                (pk, json.dumps(data), ttl),
            )


def _get(pk: str) -> dict | None:
    _ensure_schema()
    with _conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT data, ttl FROM kv_store WHERE pk = %s",
                (pk,),
            )
            row = cur.fetchone()
            if not row:
                return None
            # Check TTL
            if row["ttl"] and row["ttl"] < int(time.time()):
                cur.execute("DELETE FROM kv_store WHERE pk = %s", (pk,))
                return None
            return row["data"]


def _delete(pk: str) -> bool:
    _ensure_schema()
    with _conn() as c:
        with c.cursor() as cur:
            cur.execute("DELETE FROM kv_store WHERE pk = %s", (pk,))
            return cur.rowcount > 0


def _list_by_prefix(prefix: str, limit: int = 50) -> list[tuple[str, dict]]:
    _ensure_schema()
    with _conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """
                SELECT pk, data FROM kv_store
                WHERE pk LIKE %s AND (ttl IS NULL OR ttl > EXTRACT(EPOCH FROM NOW())::BIGINT)
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (f"{prefix}%", limit),
            )
            return [(row["pk"], row["data"]) for row in cur.fetchall()]


# ── Etsy Credentials ──

def save_credentials(api_key, access_token, refresh_token, user_id, shop_id=None):
    _put("etsy_credentials", {
        "api_key": api_key,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": user_id,
        "shop_id": shop_id or "",
    })


def load_credentials():
    data = _get("etsy_credentials")
    if not data:
        return None
    return {
        "api_key": data["api_key"],
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user_id": data["user_id"],
        "shop_id": data.get("shop_id") or None,
    }


def delete_credentials():
    _delete("etsy_credentials")


# ── OAuth State ──

def save_oauth_state(state, verifier, redirect_uri):
    _put(f"oauth_state#{state}",
         {"verifier": verifier, "redirect_uri": redirect_uri},
         ttl_seconds=600)


def load_oauth_state(state):
    data = _get(f"oauth_state#{state}")
    if not data:
        return None
    _delete(f"oauth_state#{state}")
    return data


# ── Publish Jobs ──

def create_job(job_id):
    _put(f"job#{job_id}", {"status": "pending"}, ttl_seconds=86400)


def update_job(job_id, status, result=None, error=None):
    data = {"status": status}
    if result:
        data["result"] = result
    if error:
        data["error"] = error
    _put(f"job#{job_id}", data, ttl_seconds=86400)


def get_job(job_id):
    return _get(f"job#{job_id}")


# ── Listings ──

def save_listing(listing_id, title, tags, description, price=None, s3_key=None,
                 sizes=None, etsy_listing_id=None, etsy_listing_url=None,
                 preview_url=None):
    now = int(time.time())
    data = {
        "listing_id": listing_id,
        "title": title,
        "tags": tags,
        "description": description,
        "created_at": now,
        "price": price,
        "s3_key": s3_key,
        "sizes": sizes or [],
        "etsy_listing_id": etsy_listing_id,
        "etsy_listing_url": etsy_listing_url,
        "preview_url": preview_url,
    }
    _put(f"listing#{listing_id}", data)
    return _listing_to_dict(data)


def list_listings(limit=50):
    items = _list_by_prefix("listing#", limit=limit)
    return [_listing_to_dict(data) for _, data in items]


def get_listing(listing_id):
    data = _get(f"listing#{listing_id}")
    return _listing_to_dict(data) if data else None


def delete_listing(listing_id):
    return _delete(f"listing#{listing_id}")


# ── Custom Templates ──

def save_custom_template(template_id, name, s3_key, orientation="vertical",
                         frame_bbox=None):
    data = {
        "template_id": template_id,
        "name": name,
        "s3_key": s3_key,
        "orientation": orientation,
        "frame_bbox": frame_bbox,
        "created_at": int(time.time()),
    }
    _put(f"template#{template_id}", data)
    return _template_to_dict(data)


def list_custom_templates():
    items = _list_by_prefix("template#", limit=100)
    return [_template_to_dict(data) for _, data in items]


def delete_custom_template(template_id):
    return _delete(f"template#{template_id}")


def _listing_to_dict(data):
    if not data:
        return None
    return {
        "id": data.get("listing_id", ""),
        "title": data.get("title", ""),
        "tags": data.get("tags", []),
        "description": data.get("description", ""),
        "price": float(data["price"]) if data.get("price") is not None else None,
        "s3_key": data.get("s3_key"),
        "sizes": data.get("sizes", []),
        "etsy_listing_id": data.get("etsy_listing_id"),
        "etsy_listing_url": data.get("etsy_listing_url"),
        "preview_url": data.get("preview_url"),
        "created_at": data.get("created_at", 0),
    }


def _template_to_dict(data):
    return {
        "id": data.get("template_id", ""),
        "name": data.get("name", ""),
        "s3_key": data.get("s3_key", ""),
        "orientation": data.get("orientation", "vertical"),
        "frame_bbox": data.get("frame_bbox"),
        "is_custom": True,
        "created_at": data.get("created_at", 0),
    }
