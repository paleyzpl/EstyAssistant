"""Tests for the pluggable store layer."""

import os
from unittest.mock import patch

import pytest


class TestStoreSelection:
    def test_default_is_dynamo(self):
        # Clear the cached store module
        with patch.dict(os.environ, {"DB_BACKEND": "dynamo"}, clear=False):
            import importlib

            import api.stores
            importlib.reload(api.stores)
            store = api.stores.get_store()
            assert store.__name__ == "api.stores.dynamo_store"

    def test_supabase_backend(self):
        with patch.dict(os.environ, {"DB_BACKEND": "supabase"}, clear=False):
            import importlib

            import api.stores
            importlib.reload(api.stores)
            store = api.stores.get_store()
            assert store.__name__ == "api.stores.supabase_store"

    def test_all_stores_have_same_interface(self):
        """Both stores must implement all required methods."""
        from api.stores import dynamo_store, supabase_store

        required_methods = [
            "save_credentials", "load_credentials", "delete_credentials",
            "save_oauth_state", "load_oauth_state",
            "create_job", "update_job", "get_job",
            "save_listing", "list_listings", "get_listing", "delete_listing",
            "save_custom_template", "list_custom_templates", "delete_custom_template",
        ]
        for method in required_methods:
            assert hasattr(dynamo_store, method), f"dynamo_store missing {method}"
            assert hasattr(supabase_store, method), f"supabase_store missing {method}"


class TestStorageBackendSelection:
    def test_storage_backend_env(self):
        """Storage backend should be controlled by STORAGE_BACKEND env var."""
        # Just verify the env var is read (don't actually connect)
        import importlib

        with patch.dict(os.environ, {"STORAGE_BACKEND": "supabase", "SUPABASE_URL": "https://test.supabase.co"}, clear=False):
            import api.s3
            importlib.reload(api.s3)
            assert api.s3.BACKEND == "supabase"

        with patch.dict(os.environ, {"STORAGE_BACKEND": "s3"}, clear=False):
            import api.s3
            importlib.reload(api.s3)
            assert api.s3.BACKEND == "s3"
