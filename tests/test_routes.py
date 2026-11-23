from pathlib import Path


def test_pages_render(client):
    wallet = client.get("/")
    new = client.get("/transaction/new")
    view = client.get("/transaction/view")
    assert wallet.status_code == 200
    assert new.status_code == 200
    assert view.status_code == 200
    assert b"Generate wallet" in wallet.data
    assert b'name="sender_private_key"' in new.data
    assert b'name="recipient_address"' in new.data
    assert b'name="stock"' in new.data
    assert b'name="quantity"' in new.data
    assert b"Mine block" in view.data
    assert b"id=\"blocks\"" in view.data
    for response in (wallet, new, view):
        assert b"Texas Tech" in response.data
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_demo_page_describes_the_mouse_and_the_exchange():
    root = Path(__file__).resolve().parents[1]
    html = (root / "demo" / "index.html").read_text(encoding="utf-8")
    script = (root / "demo" / "exchange.js").read_text(encoding="utf-8")
    assert "exchange.js" in html
    assert "styles.css" in html
    assert "Virtual mouse" in html
    assert "Maktm" in html
    assert "RSA-PSS" in script
    assert "localStorage" in script
    assert "There are no transactions to mine." in script
