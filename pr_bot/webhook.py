"""Backwards-compatible webhook entrypoint."""

from bots.app import app, handle_pull_request

# Backwards-compatible alias
handle_pull_request_opened = handle_pull_request

__all__ = ["app", "handle_pull_request", "handle_pull_request_opened"]
