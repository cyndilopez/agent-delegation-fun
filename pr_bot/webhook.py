"""Backwards-compatible webhook entrypoint."""

from bots.app import app, handle_pull_request_opened

__all__ = ["app", "handle_pull_request_opened"]
