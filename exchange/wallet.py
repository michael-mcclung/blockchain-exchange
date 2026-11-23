"""Demonstration RSA wallets.

A wallet address is the hex encoding of the public key's PEM text, the same
idea as the 2019 exchange. Keys are generated on demand and are not written
to disk. The transaction form still sends the private key to the local
process to sign, which is only reasonable for this classroom demo.

Based on wallet.py from https://github.com/Maktm/blockchain-exchange
"""

from __future__ import annotations

import binascii
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

_HEX = re.compile(r"^[0-9a-fA-F]+$")


def _pss() -> padding.PSS:
    """Salt length is the SHA-256 digest length so sign and verify agree.

    The 2019 code used ``PSS.MAX_LENGTH`` on both sides. Current versions of
    ``cryptography`` do not treat that sentinel the same way when verifying,
    so valid signatures were rejected.
    """
    return padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.DIGEST_LENGTH,
    )


def canonical_transaction(
    sender_address: str,
    recipient_address: str,
    stock: str,
    quantity: int,
) -> bytes:
    """Bytes that are signed and verified.

    Key order is fixed by ``sort_keys`` so the payload does not depend on dict
    ordering. ``str(OrderedDict(...))`` in the 2019 code was not a stable
    contract.
    """
    payload = {
        "quantity": quantity,
        "recipient_address": recipient_address,
        "sender_address": sender_address,
        "stock": stock,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class Wallet:
    """A new 2048-bit RSA key pair."""

    def __init__(self) -> None:
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()

    def get_private_key(self) -> bytes:
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def get_public_key(self) -> bytes:
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def get_json(self) -> dict[str, str]:
        return {
            "private_key": binascii.hexlify(self.get_private_key()).decode("ascii"),
            "public_key": binascii.hexlify(self.get_public_key()).decode("ascii"),
        }


def _unhex(value: str) -> bytes:
    if not isinstance(value, str) or not _HEX.fullmatch(value) or len(value) % 2:
        raise ValueError("Key is not hex-encoded PEM.")
    try:
        return binascii.unhexlify(value.encode("ascii"))
    except binascii.Error as exc:
        raise ValueError("Key is not hex-encoded PEM.") from exc


def load_private_key_hex(value: str):
    try:
        return serialization.load_pem_private_key(_unhex(value), password=None)
    except (ValueError, TypeError) as exc:
        raise ValueError("Private key could not be read.") from exc


def load_public_key_hex(value: str):
    try:
        return serialization.load_pem_public_key(_unhex(value))
    except (ValueError, TypeError) as exc:
        raise ValueError("Public key could not be read.") from exc


def public_key_matches(private_hex: str, public_hex: str) -> bool:
    private_key = load_private_key_hex(private_hex)
    public_key = load_public_key_hex(public_hex)
    return private_key.public_key().public_numbers() == public_key.public_numbers()


def sign_transaction(
    private_hex: str,
    sender_address: str,
    recipient_address: str,
    stock: str,
    quantity: int,
) -> str:
    key = load_private_key_hex(private_hex)
    signature = key.sign(
        canonical_transaction(sender_address, recipient_address, stock, quantity),
        _pss(),
        hashes.SHA256(),
    )
    return binascii.hexlify(signature).decode("ascii")


def verify_transaction(public_hex: str, signature_hex: str, transaction: dict[str, Any]) -> bool:
    try:
        key = load_public_key_hex(public_hex)
        signature = _unhex(signature_hex)
        payload = canonical_transaction(
            transaction["sender_address"],
            transaction["recipient_address"],
            transaction["stock"],
            int(transaction["quantity"]),
        )
        key.verify(signature, payload, _pss(), hashes.SHA256())
    except (InvalidSignature, ValueError, KeyError, TypeError):
        return False
    return True
