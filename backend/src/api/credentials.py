"""Credential, OAuth state, job, listing, and template store.

Thin facade that delegates to the backend selected via DB_BACKEND env var:
- "dynamo" (default): AWS DynamoDB
- "supabase": Supabase Postgres

All downstream code imports from this module, so swapping backends
requires no changes elsewhere.
"""

from api.stores import get_store

_store = get_store()


# ── Etsy Credentials ──

def save_credentials(*args, **kwargs):
    return _store.save_credentials(*args, **kwargs)


def load_credentials():
    return _store.load_credentials()


def delete_credentials():
    return _store.delete_credentials()


# ── OAuth State ──

def save_oauth_state(*args, **kwargs):
    return _store.save_oauth_state(*args, **kwargs)


def load_oauth_state(*args, **kwargs):
    return _store.load_oauth_state(*args, **kwargs)


# ── Publish Jobs ──

def create_job(*args, **kwargs):
    return _store.create_job(*args, **kwargs)


def update_job(*args, **kwargs):
    return _store.update_job(*args, **kwargs)


def get_job(*args, **kwargs):
    return _store.get_job(*args, **kwargs)


# ── Listings ──

def save_listing(*args, **kwargs):
    return _store.save_listing(*args, **kwargs)


def list_listings(*args, **kwargs):
    return _store.list_listings(*args, **kwargs)


def get_listing(*args, **kwargs):
    return _store.get_listing(*args, **kwargs)


def delete_listing(*args, **kwargs):
    return _store.delete_listing(*args, **kwargs)


# ── Custom Templates ──

def save_custom_template(*args, **kwargs):
    return _store.save_custom_template(*args, **kwargs)


def list_custom_templates(*args, **kwargs):
    return _store.list_custom_templates(*args, **kwargs)


def delete_custom_template(*args, **kwargs):
    return _store.delete_custom_template(*args, **kwargs)
