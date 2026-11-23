import pytest

from exchange.blockchain import Blockchain, InvalidTransaction, normalize_difficulty
from exchange.wallet import canonical_transaction, sign_transaction, verify_transaction


def test_canonical_payload_is_sorted_json():
    payload = canonical_transaction("pub", "recip", "AAPL", 3)
    assert payload == b'{"quantity":3,"recipient_address":"recip","sender_address":"pub","stock":"AAPL"}'


def test_difficulty_falls_back_when_unusable():
    assert normalize_difficulty("00") == "00"
    assert normalize_difficulty("AbC") == "abc"
    assert normalize_difficulty("zzzz") == "00"
    assert normalize_difficulty("0000") == "00"
    assert normalize_difficulty("") == "00"


def test_sign_and_verify_round_trip(wallets):
    sender, recipient = wallets
    signature = sign_transaction(sender["private_key"], sender["public_key"], recipient["public_key"], "TTU", 4)
    transaction = {
        "sender_address": sender["public_key"],
        "recipient_address": recipient["public_key"],
        "stock": "TTU",
        "quantity": 4,
    }
    assert verify_transaction(sender["public_key"], signature, transaction)
    transaction["quantity"] = 5
    assert not verify_transaction(sender["public_key"], signature, transaction)


def test_submit_and_mine_links_the_chain(blockchain, wallets):
    sender, recipient = wallets
    result = blockchain.submit_transaction(
        sender["public_key"],
        sender["private_key"],
        recipient["public_key"],
        "AAPL",
        2,
    )
    assert result["pending"] == 1
    assert blockchain.is_valid()
    block = blockchain.mine()
    assert block["block_number"] == 2
    assert block["previous_hash"] == blockchain.hash_block(blockchain.chain[0])
    assert blockchain.hash_block(block).startswith("0")
    assert blockchain.pending == []
    assert blockchain.is_valid()


def test_mismatched_key_is_rejected(blockchain, wallets):
    sender, recipient = wallets
    with pytest.raises(InvalidTransaction):
        blockchain.submit_transaction(
            sender["public_key"],
            recipient["private_key"],
            recipient["public_key"],
            "AAPL",
            1,
        )


def test_bad_stock_and_quantity(blockchain, wallets):
    sender, recipient = wallets
    with pytest.raises(InvalidTransaction):
        blockchain.submit_transaction(sender["public_key"], sender["private_key"], recipient["public_key"], "<script>", 1)
    with pytest.raises(InvalidTransaction):
        blockchain.submit_transaction(sender["public_key"], sender["private_key"], recipient["public_key"], "AAPL", 0)


def test_mine_without_pending(blockchain):
    from exchange.blockchain import BlockchainError

    with pytest.raises(BlockchainError):
        blockchain.mine()


def test_tampered_quantity_breaks_the_chain(blockchain, wallets):
    sender, recipient = wallets
    blockchain.submit_transaction(sender["public_key"], sender["private_key"], recipient["public_key"], "MSFT", 8)
    blockchain.mine()
    assert blockchain.is_valid()
    blockchain.chain[-1]["transactions"][0]["quantity"] = 9
    assert not blockchain.is_valid()


def test_private_key_is_not_stored_on_the_chain(blockchain, wallets):
    sender, recipient = wallets
    blockchain.submit_transaction(sender["public_key"], sender["private_key"], recipient["public_key"], "IBM", 1)
    blockchain.mine()
    snapshot = blockchain.snapshot()
    assert sender["private_key"] not in str(snapshot)
    assert snapshot["valid"] is True
    assert snapshot["chain"][1]["transactions"][0]["stock"] == "IBM"
    assert "hash" in snapshot["chain"][1]
