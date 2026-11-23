"""JSON API for wallets, transactions, and mining.

Private keys are used to sign and are not stored, logged, or returned.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from .blockchain import Blockchain, BlockchainError, InvalidTransaction
from .wallet import Wallet

api = Blueprint("api", __name__)

_FIELDS = (
    "sender_address",
    "sender_private_key",
    "recipient_address",
    "stock",
    "quantity",
)


def _chain() -> Blockchain:
    return current_app.config["BLOCKCHAIN"]


def _payload() -> dict:
    if request.form:
        return request.form
    body = request.get_json(silent=True)
    if isinstance(body, dict):
        return body
    return {}


def _quantity(raw) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        if not raw.is_integer():
            return None
        return int(raw)
    if isinstance(raw, str):
        text = raw.strip()
        if not text.isdigit():
            return None
        return int(text)
    return None


@api.get("/api/wallet/create")
def new_wallet():
    """Generate a key pair. The private key is returned once, to the caller."""
    return jsonify(Wallet().get_json())


@api.post("/api/transaction/new")
def new_transaction():
    """Check a transfer and add it to the mempool. Mining is a separate step."""
    values = _payload()
    missing = [name for name in _FIELDS if values.get(name) in (None, "")]
    if missing:
        return jsonify(error="Missing form value.", missing=missing), 400

    quantity = _quantity(values.get("quantity"))
    if quantity is None:
        return jsonify(error="Quantity must be a whole number from 1 to 1000000000."), 400

    try:
        result = _chain().submit_transaction(
            str(values.get("sender_address", "")),
            str(values.get("sender_private_key", "")),
            str(values.get("recipient_address", "")),
            str(values.get("stock", "")),
            quantity,
        )
    except InvalidTransaction as exc:
        return jsonify(error=str(exc)), 400
    except BlockchainError as exc:
        return jsonify(error=str(exc)), 400

    return jsonify(message="Transaction queued.", pending=result["pending"]), 201


@api.post("/api/mine")
def mine():
    """Seal pending transactions into the next block."""
    try:
        block = _chain().mine()
    except BlockchainError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(
        message="Block mined.",
        block_number=block["block_number"],
        nonce=block["nonce"],
        hash=_chain().hash_block(block),
        transactions=len(block["transactions"]),
    )


@api.get("/api/transaction/view")
def view_transaction():
    """Return the chain, pending transactions, and whether the links check out."""
    return jsonify(_chain().snapshot())
