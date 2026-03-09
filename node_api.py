import os

from flask import Flask, jsonify, request, render_template

from core.blockchain import Blockchain
from core.storage import load_wallets_data, save_blockchain, save_wallets
from core.transaction import Transaction, TransactionInput, TransactionOutput
from core.tx_builder import create_transaction
from wallet.wallet import Wallet
from network.node import PeerNode
from core.config import (
    COIN_NAME,
    COIN_SYMBOL,
    DECIMALS,
    MAX_SUPPLY,
    PREMINE_FOUNDER,
    PREMINE_DEV,
    PREMINE_MARKETING,
    PREMINE_TOTAL,
    MINING_ALLOCATION,
    INITIAL_BLOCK_REWARD,
    HALVING_INTERVAL,
    TESTNET_BLOCK_TIME_SECONDS,
)


app = Flask(__name__)

HOST = "127.0.0.1"
PORT = int(os.environ.get("BRVX_PORT", "5000"))
INITIAL_PEERS = [
    p.strip().rstrip("/")
    for p in os.environ.get("BRVX_PEERS", "").split(",")
    if p.strip()
]

blockchain = Blockchain()


def load_wallets():
    data = load_wallets_data()

    if not data:
        wallets = {
            "founder_wallet": Wallet(),
            "dev_wallet": Wallet(),
            "marketing_wallet": Wallet(),
            "miner_wallet": Wallet()
        }
        save_wallets(wallets)
        return wallets

    return {
        "founder_wallet": Wallet(private_key_hex=data["founder_wallet"]["private_key"]),
        "dev_wallet": Wallet(private_key_hex=data["dev_wallet"]["private_key"]),
        "marketing_wallet": Wallet(private_key_hex=data["marketing_wallet"]["private_key"]),
        "miner_wallet": Wallet(private_key_hex=data["miner_wallet"]["private_key"])
    }


wallets = load_wallets()
node = PeerNode(blockchain=blockchain, host=HOST, port=PORT, peers=INITIAL_PEERS)


def format_amount(amount):
    return amount / (10 ** DECIMALS)


def shorten(value, start=12, end=12):
    if len(value) <= start + end:
        return value
    return f"{value[:start]}...{value[-end:]}"


def rebuild_transaction_from_dict(tx_data):
    inputs = [
        TransactionInput(
            txid=i["txid"],
            output_index=i["output_index"],
            signature=i.get("signature"),
            public_key=i.get("public_key")
        )
        for i in tx_data.get("inputs", [])
    ]

    outputs = [
        TransactionOutput(
            recipient=o["recipient"],
            amount=o["amount"]
        )
        for o in tx_data.get("outputs", [])
    ]

    return Transaction(
        inputs=inputs,
        outputs=outputs,
        tx_type=tx_data.get("tx_type", "transfer"),
        timestamp=tx_data.get("timestamp"),
        nonce=tx_data.get("nonce")
    )


@app.route("/")
@app.route("/explorer")
def explorer():
    balances = {
        name: {
            "address": wallet.address,
            "balance": format_amount(blockchain.get_balance(wallet.address))
        }
        for name, wallet in wallets.items()
    }

    blocks = []
    for block in reversed(blockchain.chain[-12:]):
        block_hash = block.calculate_hash()
        blocks.append({
            "index": block.index,
            "hash": block_hash,
            "hash_short": shorten(block_hash),
            "previous_hash": block.previous_hash,
            "previous_hash_short": shorten(block.previous_hash),
            "difficulty": block.difficulty,
            "transactions_count": len(block.transactions),
            "timestamp": block.timestamp
        })

    return render_template(
        "explorer.html",
        coin_name=COIN_NAME,
        coin_symbol=COIN_SYMBOL,
        chain_height=len(blockchain.chain) - 1,
        mempool_size=blockchain.get_mempool_size(),
        total_supply=format_amount(MAX_SUPPLY),
        total_emitted=format_amount(blockchain.get_total_supply_mined()),
        total_remaining=format_amount(MAX_SUPPLY - blockchain.get_total_supply_mined()),
        premine_total=format_amount(PREMINE_TOTAL),
        premine_founder=format_amount(PREMINE_FOUNDER),
        premine_dev=format_amount(PREMINE_DEV),
        premine_marketing=format_amount(PREMINE_MARKETING),
        mining_allocation=format_amount(MINING_ALLOCATION),
        current_reward=format_amount(blockchain.get_block_reward(len(blockchain.chain))),
        initial_reward=format_amount(INITIAL_BLOCK_REWARD),
        halving_interval=HALVING_INTERVAL,
        target_block_time=TESTNET_BLOCK_TIME_SECONDS,
        peers=node.get_peers(),
        balances=balances,
        blocks=blocks
    )


@app.route("/api")
def home():
    return jsonify({
        "project": "BravaX P2P Node",
        "symbol": COIN_SYMBOL,
        "node_url": node.my_url,
        "message": "Nó BRVX online"
    })


@app.route("/node/info")
def node_info():
    return jsonify({
        "node_url": node.my_url,
        "peers": node.get_peers(),
        "chain_height": len(blockchain.chain) - 1,
        "mempool_size": blockchain.get_mempool_size(),
        "total_mined": format_amount(blockchain.get_total_supply_mined())
    })


@app.route("/node/peers", methods=["GET", "POST"])
def node_peers():
    if request.method == "GET":
        return jsonify({
            "node_url": node.my_url,
            "peers": node.get_peers()
        })

    data = request.get_json(silent=True) or {}
    peer = (data.get("peer") or "").rstrip("/")

    if not peer:
        return jsonify({"error": "Peer não informado"}), 400

    added = node.register_peer(peer)

    return jsonify({
        "added": added,
        "peers": node.get_peers()
    })


@app.route("/node/chain")
def node_chain():
    return jsonify(blockchain.export_data())


@app.route("/node/push-chain", methods=["POST"])
def node_push_chain():
    data = request.get_json(silent=True) or {}
    incoming = data.get("blockchain")

    if not incoming:
        return jsonify({"error": "Blockchain não enviada"}), 400

    try:
        replaced = blockchain.replace_with_longer_chain(incoming)
        return jsonify({
            "replaced": replaced,
            "chain_height": len(blockchain.chain) - 1
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/node/sync", methods=["POST"])
def node_sync():
    replaced = node.sync_with_peers()
    return jsonify({
        "replaced": replaced,
        "chain_height": len(blockchain.chain) - 1
    })


@app.route("/node/transaction", methods=["POST"])
def node_transaction():
    data = request.get_json(silent=True) or {}
    tx_data = data.get("transaction")

    if not tx_data:
        return jsonify({"error": "Transação não enviada"}), 400

    try:
        tx = rebuild_transaction_from_dict(tx_data)
        blockchain.add_transaction(tx)
        save_blockchain(blockchain)

        return jsonify({
            "accepted": True,
            "mempool_size": blockchain.get_mempool_size()
        })
    except Exception as e:
        return jsonify({"accepted": False, "error": str(e)}), 400


@app.route("/node/send", methods=["POST"])
def node_send():
    data = request.get_json(silent=True) or {}

    sender_name = data.get("sender")
    recipient_name = data.get("recipient")
    amount = data.get("amount")

    if sender_name not in wallets or recipient_name not in wallets:
        return jsonify({"error": "Carteira inválida"}), 400

    if amount is None:
        return jsonify({"error": "Valor não informado"}), 400

    try:
        amount_smallest = int(float(amount) * (10 ** DECIMALS))

        tx = create_transaction(
            blockchain=blockchain,
            sender_wallet=wallets[sender_name],
            recipient_address=wallets[recipient_name].address,
            amount=amount_smallest
        )

        blockchain.add_transaction(tx)
        save_blockchain(blockchain)

        broadcast_results = node.broadcast_transaction(tx)

        return jsonify({
            "accepted": True,
            "mempool_size": blockchain.get_mempool_size(),
            "broadcast_results": broadcast_results
        })
    except Exception as e:
        return jsonify({"accepted": False, "error": str(e)}), 400


@app.route("/node/mine", methods=["POST"])
def node_mine():
    data = request.get_json(silent=True) or {}

    miner_name = data.get("miner")
    miner_address = data.get("miner_address")

    try:
        if miner_address:
            blockchain.mine_pending_transactions(miner_address)
        else:
            if not miner_name:
                miner_name = "miner_wallet"

            if miner_name not in wallets:
                return jsonify({"error": "Carteira do minerador inválida"}), 400

            blockchain.mine_pending_transactions(wallets[miner_name].address)

        save_blockchain(blockchain)
        broadcast_results = node.broadcast_chain()

        return jsonify({
            "mined": True,
            "chain_height": len(blockchain.chain) - 1,
            "mempool_size": blockchain.get_mempool_size(),
            "broadcast_results": broadcast_results
        })
    except Exception as e:
        return jsonify({"mined": False, "error": str(e)}), 400


@app.route("/node/premine", methods=["POST"])
def node_premine():
    try:
        created = blockchain.initialize_premine(
            founder_address=wallets["founder_wallet"].address,
            dev_address=wallets["dev_wallet"].address,
            marketing_address=wallets["marketing_wallet"].address
        )

        save_blockchain(blockchain)
        broadcast_results = node.broadcast_chain()

        return jsonify({
            "premine_created": created,
            "chain_height": len(blockchain.chain) - 1,
            "total_mined": format_amount(blockchain.get_total_supply_mined()),
            "broadcast_results": broadcast_results
        })
    except Exception as e:
        return jsonify({"premine_created": False, "error": str(e)}), 400


@app.route("/node/balances")
def node_balances():
    return jsonify({
        name: {
            "address": wallet.address,
            "balance": format_amount(blockchain.get_balance(wallet.address))
        }
        for name, wallet in wallets.items()
    })


if __name__ == "__main__":
    print(f"Nó BRVX iniciando em {HOST}:{PORT}")
    print(f"Peers iniciais: {INITIAL_PEERS}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
