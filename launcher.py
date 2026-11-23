"""Open the blockchain exchange or the face-controlled virtual mouse.

The 2020 Tkinter launcher (SE1_GUI.py, Michael McClung) offered the same two
choices and assumed the exchange was already running. This script can start
the exchange, then open it in a browser. Without Tk, or without a display,
use a subcommand:

    python launcher.py exchange
    python launcher.py mouse
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def exchange_host() -> str:
    return os.environ.get("EXCHANGE_HOST", "127.0.0.1").strip() or "127.0.0.1"


def exchange_port() -> int:
    raw = os.environ.get("PORT", os.environ.get("EXCHANGE_PORT", "5000"))
    try:
        port = int(str(raw).strip())
    except (TypeError, ValueError):
        return 5000
    if 1 <= port <= 65535:
        return port
    return 5000


def browser_host(host: str | None = None) -> str:
    value = exchange_host() if host is None else host
    if value in {"0.0.0.0", "::"}:
        return "127.0.0.1"
    return value


def exchange_url() -> str:
    return f"http://{browser_host()}:{exchange_port()}/"


def port_is_open(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_exchange(timeout: float = 15) -> bool:
    deadline = time.time() + timeout
    host = browser_host()
    port = exchange_port()
    while time.time() < deadline:
        if port_is_open(host, port):
            return True
        time.sleep(0.15)
    return False


def start_exchange_process() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "exchange"],
        cwd=ROOT,
        start_new_session=True,
    )


def open_exchange(start: bool = True) -> int:
    """Open the exchange in a browser, starting it when the port is closed."""
    url = exchange_url()
    if port_is_open(browser_host(), exchange_port()):
        sys.stdout.write(f"Exchange already running at {url}\n")
        webbrowser.open(url)
        return 0
    if not start:
        sys.stderr.write(f"Nothing is listening at {url}. Start it with: python -m exchange\n")
        return 1
    sys.stdout.write(f"Starting the exchange at {url}\n")
    start_exchange_process()
    if not wait_for_exchange():
        sys.stderr.write("The exchange did not start. Run `python -m exchange` to see the error.\n")
        return 1
    webbrowser.open(url)
    return 0


def run_exchange_foreground(open_browser: bool) -> int:
    url = exchange_url()
    if port_is_open(browser_host(), exchange_port()):
        sys.stdout.write(f"Exchange already running at {url}\n")
        if open_browser:
            webbrowser.open(url)
        return 0
    if open_browser:
        threading.Thread(target=_open_when_ready, daemon=True).start()
    from exchange.main import main

    main()
    return 0


def _open_when_ready() -> None:
    if wait_for_exchange():
        webbrowser.open(exchange_url())


def run_mouse() -> int:
    completed = subprocess.run([sys.executable, "-m", "virtual_mouse"], cwd=ROOT)
    return completed.returncode


def launch_gui() -> int:
    import tkinter as tk
    from tkinter import messagebox, ttk

    root = tk.Tk()
    root.title("Virtual Stock Exchange")
    root.geometry("460x230")
    root.minsize(420, 210)

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Virtual Stock Exchange").grid(row=0, column=0, columnspan=2, sticky="w")
    ttk.Label(
        frame,
        text="Open the blockchain exchange, or start the face-controlled mouse.",
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 12))

    selected = tk.IntVar(value=1)
    ttk.Radiobutton(frame, text="Block Chain", value=1, variable=selected).grid(row=2, column=0, sticky="w")
    ttk.Radiobutton(frame, text="Virtual Mouse", value=2, variable=selected).grid(row=3, column=0, sticky="w")

    def choose() -> None:
        if selected.get() == 1:
            code = open_exchange(start=True)
            if code != 0:
                messagebox.showerror("Block Chain", "The exchange did not start. See the terminal for details.")
            return
        code = run_mouse()
        if code != 0:
            messagebox.showerror(
                "Virtual Mouse",
                "The virtual mouse stopped. If this is the first run, install "
                "requirements-mouse.txt and download the landmark model. "
                "The terminal has the exact message.",
            )

    buttons = ttk.Frame(frame)
    buttons.grid(row=4, column=0, columnspan=2, sticky="w", pady=(16, 0))
    ttk.Button(buttons, text="Select", command=choose).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(buttons, text="Exit", command=root.destroy).grid(row=0, column=1)

    root.mainloop()
    return 0


def _gui_available() -> bool:
    if sys.platform == "linux" and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return False
    try:
        import tkinter  # noqa: F401
    except Exception:
        return False
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open the blockchain exchange or the virtual mouse.")
    parser.add_argument("command", nargs="?", choices=("exchange", "mouse"))
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="With `exchange`, run the server in this terminal and do not open a browser.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "exchange":
        return run_exchange_foreground(open_browser=not args.no_browser)
    if args.command == "mouse":
        return run_mouse()
    if _gui_available():
        try:
            return launch_gui()
        except Exception as exc:
            sys.stderr.write(f"The windowed launcher could not start ({exc}).\n")
    sys.stdout.write(
        "Launcher commands:\n"
        "  python launcher.py exchange\n"
        "  python launcher.py mouse\n"
        "Install Tk (for example python3-tk) and a display to use the window.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
