"""Start the unified agent webhook server."""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent webhook server")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("bots.app:app", host="0.0.0.0", port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
