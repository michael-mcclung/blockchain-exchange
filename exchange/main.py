"""Start the exchange on localhost.

Host and port come from the environment so nothing environment-specific is
hard-coded into the process:

- ``EXCHANGE_HOST`` (default ``127.0.0.1``)
- ``PORT`` if set, otherwise ``EXCHANGE_PORT`` (default ``5000``)
- ``EXCHANGE_DEBUG`` set to ``1`` turns on the Flask debugger

The auto-reloader stays off. A reloader would fork a second process with a
second chain, and a transaction mined in one would not show in the other.
"""

from __future__ import annotations

import os
import sys

from . import create_app


def bind_host() -> str:
    return os.environ.get("EXCHANGE_HOST", "127.0.0.1").strip() or "127.0.0.1"


def bind_port() -> int:
    raw = os.environ.get("PORT", os.environ.get("EXCHANGE_PORT", "5000"))
    try:
        port = int(raw)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Port must be an integer (got {raw!r}).") from exc
    if not 1 <= port <= 65535:
        raise SystemExit(f"Port must be between 1 and 65535 (got {port}).")
    return port


def main() -> None:
    host = bind_host()
    port = bind_port()
    debug = os.environ.get("EXCHANGE_DEBUG", "").lower() in {"1", "true", "yes"}
    app = create_app()
    shown = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    sys.stdout.write(f"Blockchain exchange at http://{shown}:{port}/\n")
    sys.stdout.write("The chain is kept in memory and clears when this process stops.\n")
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    main()
