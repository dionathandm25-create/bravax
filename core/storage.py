import os
import json

from core.block import Block

DATA_DIR = os.environ.get("BRVX_DATA_DIR", "data")

BLOCKCHAIN_FILE = os.path.join(DATA_DIR, "blockchain.json")
WALLETS_FILE = os.path.join(DATA_DIR, "wallets.json")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def save_blockchain(blockchain):
    ensure_data_dir()

    with open(BLOCKCHAIN_FILE, "w", encoding="utf-8") as f:
        json.dump(blockchain.export_data(), f, indent=2)


def load_blockchain_data():
    ensure_data_dir()

    if not os.path.exists(BLOCKCHAIN_FILE):
        return None

    if os.path.getsize(BLOCKCHAIN_FILE) == 0:
        return None

    with open(BLOCKCHAIN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def rebuild_chain(chain_data):
    rebuilt_chain = []

    for block_data in chain_data:
        block = Block(
            index=block_data["index"],
            previous_hash=block_data["previous_hash"],
            transactions=block_data["transactions"],
            timestamp=block_data["timestamp"],
            nonce=block_data["nonce"],
            difficulty=block_data["difficulty"]
        )
        rebuilt_chain.append(block)

    return rebuilt_chain


def save_wallets(wallets):
    ensure_data_dir()

    data = {
        name: wallet.to_dict()
        for name, wallet in wallets.items()
    }

    with open(WALLETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_wallets_data():
    ensure_data_dir()

    if not os.path.exists(WALLETS_FILE):
        return None

    if os.path.getsize(WALLETS_FILE) == 0:
        return None

    with open(WALLETS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
