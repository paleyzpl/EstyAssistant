"""DynamoDB-backed credential and job store for the web backend."""

import json
import logging
import os
import time

import boto3

logger = logging.getLogger(__name__)

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "etsy-assistant-credentials")
REGION = os.environ.get("AWS_REGION", "us-east-1")

_table = None


def _get_table():
    global _table
    if _table is None:
        dynamodb = boto3.resource("dynamodb", region_name=REGION)
        _table = dynamodb.Table(TABLE_NAME)
    return _table


# ── Etsy Credentials ──

def save_credentials(api_key: str, access_token: str, refresh_token: str,
                     user_id: str, shop_id: str | None = None) -> None:
    """Save Etsy OAuth credentials to DynamoDB."""
    table = _get_table()
    table.put_item(Item={
        "pk": "etsy_credentials",
        "api_key": api_key,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": user_id,
        "shop_id": shop_id or "",
        "updated_at": int(time.time()),
    })
    logger.info("Saved Etsy credentials to DynamoDB")


def load_credentials() -> dict | None:
    """Load Etsy OAuth credentials from DynamoDB. Returns None if not found."""
    table = _get_table()
    resp = table.get_item(Key={"pk": "etsy_credentials"})
    item = resp.get("Item")
    if not item:
        return None
    return {
        "api_key": item["api_key"],
        "access_token": item["access_token"],
        "refresh_token": item["refresh_token"],
        "user_id": item["user_id"],
        "shop_id": item.get("shop_id") or None,
    }


def delete_credentials() -> None:
    """Delete Etsy OAuth credentials from DynamoDB."""
    table = _get_table()
    table.delete_item(Key={"pk": "etsy_credentials"})
    logger.info("Deleted Etsy credentials from DynamoDB")


# ── OAuth State (PKCE verifier + state) ──

def save_oauth_state(state: str, verifier: str, redirect_uri: str) -> None:
    """Save OAuth PKCE state for callback verification. TTL: 10 minutes."""
    table = _get_table()
    table.put_item(Item={
        "pk": f"oauth_state#{state}",
        "verifier": verifier,
        "redirect_uri": redirect_uri,
        "ttl": int(time.time()) + 600,
    })


def load_oauth_state(state: str) -> dict | None:
    """Load and delete OAuth state. Returns None if expired/missing."""
    table = _get_table()
    resp = table.get_item(Key={"pk": f"oauth_state#{state}"})
    item = resp.get("Item")
    if not item:
        return None
    # Clean up
    table.delete_item(Key={"pk": f"oauth_state#{state}"})
    return {
        "verifier": item["verifier"],
        "redirect_uri": item["redirect_uri"],
    }


# ── Publish Jobs ──

def create_job(job_id: str) -> None:
    """Create a pending publish job."""
    table = _get_table()
    table.put_item(Item={
        "pk": f"job#{job_id}",
        "status": "pending",
        "created_at": int(time.time()),
        "ttl": int(time.time()) + 86400,  # 24h TTL
    })


def update_job(job_id: str, status: str, result: dict | None = None,
               error: str | None = None) -> None:
    """Update job status."""
    table = _get_table()
    item = {
        "pk": f"job#{job_id}",
        "status": status,
        "updated_at": int(time.time()),
        "ttl": int(time.time()) + 86400,
    }
    if result:
        item["result"] = json.dumps(result)
    if error:
        item["error"] = error
    table.put_item(Item=item)


def get_job(job_id: str) -> dict | None:
    """Get job status. Returns None if not found."""
    table = _get_table()
    resp = table.get_item(Key={"pk": f"job#{job_id}"})
    item = resp.get("Item")
    if not item:
        return None
    out = {"status": item["status"]}
    if "result" in item:
        out["result"] = json.loads(item["result"])
    if "error" in item:
        out["error"] = item["error"]
    return out


# ── Listing History ──

def save_listing(listing_id: str, title: str, tags: list[str],
                 description: str, price: float | None = None,
                 s3_key: str | None = None, sizes: list[str] | None = None,
                 etsy_listing_id: str | None = None,
                 etsy_listing_url: str | None = None,
                 preview_url: str | None = None) -> dict:
    """Save a listing to history. Returns the saved item."""
    table = _get_table()
    now = int(time.time())
    item = {
        "pk": f"listing#{listing_id}",
        "sk": f"listing#{now}",
        "listing_id": listing_id,
        "title": title,
        "tags": tags,
        "description": description,
        "created_at": now,
    }
    if price is not None:
        item["price"] = str(price)
    if s3_key:
        item["s3_key"] = s3_key
    if sizes:
        item["sizes"] = sizes
    if etsy_listing_id:
        item["etsy_listing_id"] = etsy_listing_id
    if etsy_listing_url:
        item["etsy_listing_url"] = etsy_listing_url
    if preview_url:
        item["preview_url"] = preview_url

    table.put_item(Item=item)
    logger.info("Saved listing %s: %s", listing_id, title[:40])
    return _listing_to_dict(item)


def list_listings(limit: int = 50) -> list[dict]:
    """List saved listings, most recent first."""
    table = _get_table()
    from boto3.dynamodb.conditions import Key as DDBKey

    # Scan for listing items (single-user, small table)
    resp = table.scan(
        FilterExpression=DDBKey("pk").begins_with("listing#"),
        Limit=limit * 3,  # over-fetch since scan returns all items
    )
    items = resp.get("Items", [])
    items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return [_listing_to_dict(item) for item in items[:limit]]


def get_listing(listing_id: str) -> dict | None:
    """Get a single listing by ID."""
    table = _get_table()
    # Need to scan since we don't know the sort key
    from boto3.dynamodb.conditions import Key as DDBKey

    resp = table.scan(
        FilterExpression=DDBKey("pk").eq(f"listing#{listing_id}"),
        Limit=1,
    )
    items = resp.get("Items", [])
    if not items:
        return None
    return _listing_to_dict(items[0])


def delete_listing(listing_id: str) -> bool:
    """Delete a listing from history. Returns True if deleted."""
    table = _get_table()
    from boto3.dynamodb.conditions import Key as DDBKey

    # Find the item to get its sort key
    resp = table.scan(
        FilterExpression=DDBKey("pk").eq(f"listing#{listing_id}"),
        Limit=1,
    )
    items = resp.get("Items", [])
    if not items:
        return False

    table.delete_item(Key={"pk": items[0]["pk"]})
    logger.info("Deleted listing %s", listing_id)
    return True


def _listing_to_dict(item: dict) -> dict:
    """Convert a DynamoDB listing item to a clean dict."""
    return {
        "id": item.get("listing_id", ""),
        "title": item.get("title", ""),
        "tags": item.get("tags", []),
        "description": item.get("description", ""),
        "price": float(item["price"]) if "price" in item else None,
        "s3_key": item.get("s3_key"),
        "sizes": item.get("sizes", []),
        "etsy_listing_id": item.get("etsy_listing_id"),
        "etsy_listing_url": item.get("etsy_listing_url"),
        "preview_url": item.get("preview_url"),
        "created_at": item.get("created_at", 0),
    }
