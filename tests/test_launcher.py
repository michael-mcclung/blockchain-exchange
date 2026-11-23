import socket
import sys

import pytest

from exchange.main import bind_port
from launcher import browser_host, build_parser, exchange_url, main, port_is_open


def test_browser_host_rewrites_wildcard(monkeypatch):
    monkeypatch.setenv("EXCHANGE_HOST", "0.0.0.0")
    monkeypatch.setenv("EXCHANGE_PORT", "5000")
    monkeypatch.delenv("PORT", raising=False)
    assert browser_host() == "127.0.0.1"
    assert exchange_url() == "http://127.0.0.1:5000/"


def test_parser_commands():
    args = build_parser().parse_args(["exchange", "--no-browser"])
    assert args.command == "exchange"
    assert args.no_browser is True
    assert build_parser().parse_args(["mouse"]).command == "mouse"


def test_port_listener_round_trip():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    try:
        assert port_is_open("127.0.0.1", port) is True
    finally:
        sock.close()
    assert port_is_open("127.0.0.1", port) is False


def test_launcher_without_a_window_explains_the_commands(monkeypatch, capsys):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    assert main([]) == 1
    assert "python launcher.py exchange" in capsys.readouterr().out


def test_bad_port_exits(monkeypatch):
    monkeypatch.setenv("EXCHANGE_PORT", "nope")
    monkeypatch.delenv("PORT", raising=False)
    with pytest.raises(SystemExit):
        bind_port()
