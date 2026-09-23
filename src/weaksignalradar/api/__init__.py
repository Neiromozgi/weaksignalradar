"""Minimal HTTP API package for Stage A (health only)."""

from weaksignalradar.api.app import app, create_app, get_app

__all__ = ["app", "create_app", "get_app"]
