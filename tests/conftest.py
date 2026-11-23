import pytest

from exchange import create_app
from exchange.blockchain import Blockchain
from exchange.wallet import Wallet


@pytest.fixture(scope="session")
def wallets():
    return Wallet().get_json(), Wallet().get_json()


@pytest.fixture
def blockchain():
    return Blockchain(difficulty_prefix="0")


@pytest.fixture
def client(blockchain):
    app = create_app(blockchain)
    app.config["TESTING"] = True
    return app.test_client()


