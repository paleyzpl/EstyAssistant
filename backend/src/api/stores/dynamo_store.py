"""DynamoDB-backed credential and job store."""

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

def save_credentials(api_key, access_token, refresh_token, user_id, shop_id=None):
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


def load_credentials():
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


def delete_credentials():
    table = _get_table()
    table.delete_item(Key={"pk": "etsy_credentials"})


# ── OAuth State ──

def save_oauth_state(state, verifier, redirect_uri):
    table = _get_table()
    table.put_item(Item={
        "pk": f"oauth_state#{state}",
        "verifier": verifier,
        "redirect_uri": redirect_uri,
        "ttl": int(time.time()) + 600,
    })


def load_oauth_state(state):
    table = _get_table()
    resp = table.get_item(Key={"pk": f"oauth_state#{state}"})
    item = resp.get("Item")
    if not item:
        return None
    table.delete_item(Key={"pk": f"oauth_state#{state}"})
    return {"verifier": item["verifier"], "redirect_uri": item["redirect_uri"]}


# ── Publish Jobs ──

def create_job(job_id):
    table = _get_table()
    table.put_item(Item={
        "pk": f"job#{job_id}",
        "status": "pending",
        "created_at": int(time.time()),
        "ttl": int(time.time()) + 86400,
    })


def update_job(job_id, status, result=None, error=None):
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


def get_job(job_id):
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


# ── Listings ──

def save_listing(listing_id, title, tags, description, price=None, s3_key=None,
                 sizes=None, etsy_listing_id=None, etsy_listing_url=None,
                 preview_url=None):
    table = _get_table()
    now = int(time.time())
    item = {
        "pk": f"listing#{listing_id}",
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
    return _listing_to_dict(item)


def list_listings(limit=50):
    table = _get_table()
    from boto3.dynamodb.conditions import Key as DDBKey
    resp = table.scan(
        FilterExpression=DDBKey("pk").begins_with("listing#"),
        Limit=limit * 3,
    )
    items = resp.get("Items", [])
    items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return [_listing_to_dict(item) for item in items[:limit]]


def get_listing(listing_id):
    table = _get_table()
    from boto3.dynamodb.conditions import Key as DDBKey
    resp = table.scan(
        FilterExpression=DDBKey("pk").eq(f"listing#{listing_id}"),
        Limit=1,
    )
    items = resp.get("Items", [])
    if not items:
        return None
    return _listing_to_dict(items[0])


def delete_listing(listing_id):
    table = _get_table()
    from boto3.dynamodb.conditions import Key as DDBKey
    resp = table.scan(
        FilterExpression=DDBKey("pk").eq(f"listing#{listing_id}"),
        Limit=1,
    )
    items = resp.get("Items", [])
    if not items:
        return False
    table.delete_item(Key={"pk": items[0]["pk"]})
    return True


# ── Custom Templates ──

def save_custom_template(template_id, name, s3_key, orientation="vertical",
                         frame_bbox=None):
    table = _get_table()
    item = {
        "pk": f"template#{template_id}",
        "template_id": template_id,
        "name": name,
        "s3_key": s3_key,
        "orientation": orientation,
        "created_at": int(time.time()),
    }
    if frame_bbox:
        item["frame_bbox"] = frame_bbox
    table.put_item(Item=item)
    return _template_to_dict(item)


def list_custom_templates():
    table = _get_table()
    from boto3.dynamodb.conditions import Key as DDBKey
    resp = table.scan(
        FilterExpression=DDBKey("pk").begins_with("template#"),
        Limit=100,
    )
    items = resp.get("Items", [])
    items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return [_template_to_dict(item) for item in items]


def delete_custom_template(template_id):
    table = _get_table()
    from boto3.dynamodb.conditions import Key as DDBKey
    resp = table.scan(
        FilterExpression=DDBKey("pk").eq(f"template#{template_id}"),
        Limit=1,
    )
    items = resp.get("Items", [])
    if not items:
        return False
    table.delete_item(Key={"pk": items[0]["pk"]})
    return True


def _listing_to_dict(item):
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


def _template_to_dict(item):
    return {
        "id": item.get("template_id", ""),
        "name": item.get("name", ""),
        "s3_key": item.get("s3_key", ""),
        "orientation": item.get("orientation", "vertical"),
        "frame_bbox": item.get("frame_bbox"),
        "is_custom": True,
        "created_at": item.get("created_at", 0),
    }
