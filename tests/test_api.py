def post_transaction(client, sender, recipient, stock="AAPL", quantity=2, **overrides):
    data = {
        "sender_address": sender["public_key"],
        "sender_private_key": sender["private_key"],
        "recipient_address": recipient["public_key"],
        "stock": stock,
        "quantity": str(quantity),
    }
    data.update(overrides)
    return client.post("/api/transaction/new", data=data)


def test_wallet_returns_hex_keys(client):
    response = client.get("/api/wallet/create")
    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {"public_key", "private_key"}
    int(body["public_key"], 16)
    int(body["private_key"], 16)
    assert response.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors" in response.headers["Content-Security-Policy"]


def test_missing_field(client):
    response = client.post("/api/transaction/new", data={"stock": "AAPL"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "Missing form value."


def test_bad_quantity(client, wallets):
    sender, recipient = wallets
    response = post_transaction(client, sender, recipient, quantity="1.5")
    assert response.status_code == 400
    response = post_transaction(client, sender, recipient, quantity="nope")
    assert response.status_code == 400


def test_mismatched_key_is_not_accepted(client, wallets):
    sender, recipient = wallets
    response = post_transaction(
        client,
        sender,
        recipient,
        sender_private_key=recipient["private_key"],
    )
    assert response.status_code == 400
    assert "match" in response.get_json()["error"]


def test_full_flow(client, blockchain, wallets):
    sender, recipient = wallets
    created = post_transaction(client, sender, recipient, stock="TXN", quantity=3)
    assert created.status_code == 201

    rejected = client.post("/api/mine")
    assert rejected.status_code == 200
    body = rejected.get_json()
    assert body["block_number"] == 2
    assert body["transactions"] == 1
    assert body["hash"].startswith("0")

    again = client.post("/api/mine")
    assert again.status_code == 400

    view = client.get("/api/transaction/view")
    payload = view.get_json()
    assert payload["length"] == 2
    assert isinstance(payload["chain"], list)
    assert payload["chain"][0]["transactions"] == []
    assert payload["chain"][1]["transactions"][0]["stock"] == "TXN"
    assert payload["chain"][1]["transactions"][0]["quantity"] == 3
    assert payload["pending"] == []
    assert payload["valid"] is True
    assert sender["private_key"] not in view.get_data(as_text=True)
    assert len(blockchain.chain) == 2


def test_json_body_is_accepted(client, wallets):
    sender, recipient = wallets
    response = client.post(
        "/api/transaction/new",
        json={
            "sender_address": sender["public_key"],
            "sender_private_key": sender["private_key"],
            "recipient_address": recipient["public_key"],
            "stock": "JSON",
            "quantity": 6,
        },
    )
    assert response.status_code == 201


def test_oversized_form_is_rejected(client):
    response = client.post("/api/transaction/new", data={"sender_address": "a" * 70000})
    assert response.status_code == 413
