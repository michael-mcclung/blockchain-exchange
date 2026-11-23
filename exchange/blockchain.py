"""In-memory blockchain for stock-ticker transfers.

Pending transactions are signed, then mining seals them into a block. The
2019 code mined inside ``submit_transaction`` with ``randrange`` as the nonce,
so the nonce did not depend on the block. Mining is now its own step, and the
nonce is the first value whose block hash starts with the difficulty prefix.

The chain is not saved. Restarting the process starts over at the genesis block.

Based on blockchain.py from https://github.com/Maktm/blockchain-exchange
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from time import time
from typing import Any

from .wallet import load_public_key_hex, public_key_matches, sign_transaction, verify_transaction

_TICKER = re.compile(r"^[A-Za-z0-9.\-]{1,16}$")
_HEX_DIGIT = frozenset("0123456789abcdef")


class BlockchainError(Exception):
    """A chain operation the caller can show to a person."""


class InvalidTransaction(BlockchainError):
    """Validation or the signature check failed."""


def normalize_difficulty(value: str) -> str:
    """Return a 1–3 character hex prefix, or ``00`` when the value is unusable."""
    prefix = value.strip().lower()
    if 1 <= len(prefix) <= 3 and all(character in _HEX_DIGIT for character in prefix):
        return prefix
    return "00"


class Blockchain:
    def __init__(self, difficulty_prefix: str | None = None) -> None:
        chosen = difficulty_prefix if difficulty_prefix is not None else os.environ.get("POW_PREFIX", "00")
        self.difficulty_prefix = normalize_difficulty(chosen)
        self.pending: list[dict[str, Any]] = []
        self.chain: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self.chain.append(
            self._assemble_block(
                block_number=1,
                timestamp=time(),
                transactions=[],
                nonce=0,
                previous_hash="00",
            )
        )

    def hash_block(self, block: dict[str, Any]) -> str:
        """SHA-256 hex of the block. A display-only ``hash`` key is ignored."""
        payload = {key: value for key, value in block.items() if key != "hash"}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def submit_transaction(
        self,
        sender_address: str,
        sender_private_key: str,
        recipient_address: str,
        stock: str,
        quantity: int,
    ) -> dict[str, Any]:
        sender_address = sender_address.strip() if isinstance(sender_address, str) else sender_address
        recipient_address = recipient_address.strip() if isinstance(recipient_address, str) else recipient_address
        stock = stock.strip() if isinstance(stock, str) else stock
        self._validate_fields(sender_address, recipient_address, stock, quantity)

        try:
            matches = public_key_matches(sender_private_key, sender_address)
        except ValueError as exc:
            raise InvalidTransaction("Sender private key or address could not be read.") from exc
        if not matches:
            raise InvalidTransaction("The private key does not match the sender address.")

        try:
            load_public_key_hex(recipient_address)
        except ValueError as exc:
            raise InvalidTransaction("Recipient address is not a public key.") from exc

        try:
            signature = sign_transaction(
                sender_private_key,
                sender_address,
                recipient_address,
                stock,
                quantity,
            )
        except ValueError as exc:
            raise InvalidTransaction("The transaction could not be signed.") from exc

        transaction = {
            "sender_address": sender_address,
            "recipient_address": recipient_address,
            "stock": stock,
            "quantity": quantity,
            "signature": signature,
        }
        if not verify_transaction(sender_address, signature, transaction):
            raise InvalidTransaction("The signature could not be verified.")

        with self._lock:
            self.pending.append(transaction)
            pending = len(self.pending)
        return {"pending": pending}

    def mine(self) -> dict[str, Any]:
        with self._lock:
            if not self.pending:
                raise BlockchainError("There are no transactions to mine.")
            transactions = json.loads(json.dumps(self.pending))
            previous_hash = self.hash_block(self.chain[-1])
            block_number = len(self.chain) + 1
            timestamp = time()
            nonce = self._proof_of_work(block_number, timestamp, transactions, previous_hash)
            block = self._assemble_block(block_number, timestamp, transactions, nonce, previous_hash)
            self.pending = []
            self.chain.append(block)
            return json.loads(json.dumps(block))

    def is_valid(self) -> bool:
        with self._lock:
            chain = json.loads(json.dumps(self.chain))
        return self._chain_is_valid(chain)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            chain = json.loads(json.dumps(self.chain))
            pending = json.loads(json.dumps(self.pending))
        valid = self._chain_is_valid(chain)
        for block in chain:
            block["hash"] = self.hash_block(block)
        return {
            "chain": chain,
            "length": len(chain),
            "pending": pending,
            "valid": valid,
            "difficulty_prefix": self.difficulty_prefix,
        }

    def _validate_fields(self, sender: Any, recipient: Any, stock: Any, quantity: Any) -> None:
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 1_000_000_000:
            raise InvalidTransaction("Quantity must be a whole number from 1 to 1000000000.")
        if not isinstance(stock, str) or not _TICKER.fullmatch(stock):
            raise InvalidTransaction("Stock must be 1 to 16 characters: letters, numbers, dot, or dash.")
        for label, value in (("Sender address", sender), ("Recipient address", recipient)):
            if not isinstance(value, str) or not value:
                raise InvalidTransaction(f"{label} is required.")
            if len(value) > 8000:
                raise InvalidTransaction(f"{label} is too long.")

    def _proof_of_work(
        self,
        block_number: int,
        timestamp: float,
        transactions: list[dict[str, Any]],
        previous_hash: str,
    ) -> int:
        limit = 2_000_000
        for nonce in range(limit):
            block = self._assemble_block(block_number, timestamp, transactions, nonce, previous_hash)
            if self.hash_block(block).startswith(self.difficulty_prefix):
                return nonce
        raise BlockchainError("Proof of work did not finish. Use a shorter POW_PREFIX and try again.")

    def _assemble_block(
        self,
        block_number: int,
        timestamp: float,
        transactions: list[dict[str, Any]],
        nonce: int,
        previous_hash: str,
    ) -> dict[str, Any]:
        return {
            "block_number": block_number,
            "timestamp": timestamp,
            "transactions": transactions,
            "nonce": nonce,
            "previous_hash": previous_hash,
        }

    def _chain_is_valid(self, chain: list[dict[str, Any]]) -> bool:
        if not chain:
            return False
        genesis = chain[0]
        if genesis.get("block_number") != 1 or genesis.get("previous_hash") != "00":
            return False
        if genesis.get("transactions"):
            return False
        for index, block in enumerate(chain):
            if block.get("block_number") != index + 1:
                return False
            for transaction in block.get("transactions") or []:
                if not verify_transaction(
                    transaction.get("sender_address", ""),
                    transaction.get("signature", ""),
                    transaction,
                ):
                    return False
            if index == 0:
                continue
            previous = chain[index - 1]
            if block.get("previous_hash") != self.hash_block(previous):
                return False
            if not self.hash_block(block).startswith(self.difficulty_prefix):
                return False
        return True
