from flask import Flask, jsonify, render_template

from core.blockchain import Blockchain
from core.storage import load_wallets_data
from wallet.wallet import Wallet
from core.config import COIN_SYMBOL, DECIMALS


app = Flask(__name__)


def format_amount(amount):
    return amount / (10 ** DECIMALS)


def load_wallets():
    data = load_wallets_data()

    if not data:
        return None

    return {
        "wallet_a": Wallet(private_key_hex=data["wallet_a"]["private_key"]),
        "wallet_b": Wallet(private_key_hex=data["wallet_b"]["private_key"]),
        "miner_wallet": Wallet(private_key_hex=data["miner_wallet"]["private_key"])
    }


def get_blockchain():
    return Blockchain()


@app.route("/")
def dashboard():
    blockchain = get_blockchain()
    wallets = load_wallets()

    balances = {}
    if wallets:
        for name, wallet in wallets.items():
            balances[name] = {
                "address": wallet.address,
                "balance": format_amount(blockchain.get_balance(wallet.address))
            }

    blocks = []
    for block in reversed(blockchain.chain):
        blocks.append({
            "index": block.index,
            "hash": block.calculate_hash(),
            "previous_hash": block.previous_hash,
            "difficulty": block.difficulty,
            "transactions_count": len(block.transactions),
            "timestamp": block.timestamp
        })

    return render_template(
        "index.html",
        coin_symbol=COIN_SYMBOL,
        chain_height=len(blockchain.chain) - 1,
        mempool_size=blockchain.get_mempool_size(),
        total_mined=format_amount(blockchain.get_total_supply_mined()),
        balances=balances,
        blocks=blocks
    )


@app.route("/api")
def home():
    return jsonify({
        "project": "BravaX",
        "symbol": COIN_SYMBOL,
        "message": "API local da BRVX online"
    })


@app.route("/status")
def status():
    blockchain = get_blockchain()
    wallets = load_wallets()

    balances = {}
    if wallets:
        for name, wallet in wallets.items():
            balances[name] = {
                "address": wallet.address,
                "balance": format_amount(blockchain.get_balance(wallet.address))
            }

    return jsonify({
        "chain_height": len(blockchain.chain) - 1,
        "mempool_size": blockchain.get_mempool_size(),
        "total_mined": format_amount(blockchain.get_total_supply_mined()),
        "symbol": COIN_SYMBOL,
        "balances": balances
    })


@app.route("/wallets")
def wallets():
    loaded = load_wallets()

    if not loaded:
        return jsonify({"error": "Carteiras não encontradas"}), 404

    return jsonify({
        name: {
            "address": wallet.address
        }
        for name, wallet in loaded.items()
    })


@app.route("/balance/<wallet_name>")
def balance(wallet_name):
    blockchain = get_blockchain()
    wallets = load_wallets()

    if not wallets or wallet_name not in wallets:
        return jsonify({"error": "Carteira não encontrada"}), 404

    wallet = wallets[wallet_name]

    return jsonify({
        "wallet": wallet_name,
        "address": wallet.address,
        "balance": format_amount(blockchain.get_balance(wallet.address)),
        "symbol": COIN_SYMBOL
    })


@app.route("/utxos/<wallet_name>")
def utxos(wallet_name):
    blockchain = get_blockchain()
    wallets = load_wallets()

    if not wallets or wallet_name not in wallets:
        return jsonify({"error": "Carteira não encontrada"}), 404

    wallet = wallets[wallet_name]
    utxos = blockchain.get_utxos_for_address(wallet.address)

    return jsonify({
        "wallet": wallet_name,
        "address": wallet.address,
        "utxos": [utxo.to_dict() for utxo in utxos],
        "total": format_amount(sum(utxo.amount for utxo in utxos)),
        "symbol": COIN_SYMBOL
    })


@app.route("/chain")
def chain():
    blockchain = get_blockchain()

    return jsonify({
        "length": len(blockchain.chain),
        "blocks": [block.to_dict() for block in blockchain.chain]
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
