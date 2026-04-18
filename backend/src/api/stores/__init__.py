"""Pluggable data stores for the Etsy Assistant backend.

Selected via DB_BACKEND env var:
- "dynamo" (default): DynamoDB
- "supabase": Supabase Postgres
"""

import os

BACKEND = os.environ.get("DB_BACKEND", "dynamo")


def get_store():
    """Return the configured store module."""
    if BACKEND == "supabase":
        from api.stores import supabase_store
        return supabase_store
    from api.stores import dynamo_store
    return dynamo_store
