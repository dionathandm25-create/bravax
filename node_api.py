import os
from flask import Flask, jsonify, request

from core.blockchain import Blockchain
from core.wallet import load_wallets
from core.storage import save_blockchain
from core.tx_builder import create_transaction
from core.node import Node

app = Flask(__name__)

# ================================
# CONFIG
# ================================

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", os.environ.get("BRVX_PORT", "5000")))

DATA_DIR = os.environ.get("BRVX_DATA_DIR", "data")
INITIAL_PEERS = os.environ.get("BRVX_PEERS", "")

if INITIAL_PEERS:
    INITIAL_PEERS = INITIAL_PEERS.split(",")
else:
    INITIAL_PEERS = []

# ================================
# LOAD BLOCKCHAIN
# ================================

blockchain = Blockchain(data_dir=DATA_DIR)
wallets = load_wallets(data_dir=DATA_DIR)

node = Node(
    blockchain=blockchain,
    peers=INITIAL_PEERS
)

# ================================
# INFO
# ================================

@app.route("/")
def home():
    return jsonify({
        "coin": "BRVX",
        "name": "BravaX",
        "status": "running",
        "height": len(blockchain.chain) - 1
    })

# ================================
# NODE INFO
# ================================

@app.route("/node/info")
def node_info():

    return jsonify({
        "node_url": request.host_url,
        "chain_height": len(blockchain.chain) - 1,
        "mempool_size": blockchain.get_mempool_size(),
        "peers": node.peers,
        "total_mined": blockchain.total_mined / (10 ** 8)
    })

# ================================
# PEERS
# ================================

@app.route("/node/peers")
def node_peers():

    return jsonify({
        "node_url": request.host_url,
        "peers": node.peers
    })


@app.route("/node/peers", methods=["POST"])
def node_add_peer():

    data = request.get_json()

    peer = data.get("peer")

    added = node.add_peer(peer)

    return jsonify({
        "added": added,
        "peers": node.peers
    })

# ================================
# BALANCES
# ================================

@app.route("/node/balances")
def node_balances():

    balances = {}

    for name, wallet in wallets.items():

        balance = blockchain.get_balance(wallet.address)

        balances[name] = {
            "address": wallet.address,
            "balance": balance / (10 ** 8)
        }

    return jsonify(balances)

# ================================
# SEND
# ================================

@app.route("/node/send", methods=["POST"])
def node_send():

    data = request.get_json()

    sender = data.get("sender")
    recipient = data.get("recipient")
    amount = float(data.get("amount"))

    try:

        amount_smallest = int(amount * (10 ** 8))

        tx = create_transaction(
            blockchain=blockchain,
            sender_wallet=wallets[sender],
            recipient_address=wallets[recipient].address,
            amount=amount_smallest
        )

        blockchain.add_transaction(tx)

        broadcast_results = node.broadcast_transaction(tx)

        return jsonify({
            "accepted": True,
            "mempool_size": blockchain.get_mempool_size(),
            "broadcast_results": broadcast_results
        })

    except Exception as e:

        return jsonify({
            "accepted": False,
            "error": str(e)
        }), 400

# ================================
# MINE
# ================================

@app.route("/node/mine", methods=["POST"])
def node_mine():

    data = request.get_json(silent=True) or {}

    miner_name = data.get("miner", "miner_wallet")

    if miner_name not in wallets:

        return jsonify({
            "error": "Carteira do minerador inválida"
        }), 400

    miner_address = wallets[miner_name].address

    try:

        blockchain.mine_pending_transactions(miner_address)

        save_blockchain(blockchain)

        broadcast_results = node.broadcast_chain()

        return jsonify({
            "mined": True,
            "chain_height": len(blockchain.chain) - 1,
            "mempool_size": blockchain.get_mempool_size(),
            "broadcast_results": broadcast_results
        })

    except Exception as e:

        return jsonify({
            "mined": False,
            "error": str(e)
        }), 400

# ================================
# SYNC
# ================================

@app.route("/node/sync", methods=["POST"])
def node_sync():

    replaced = node.sync_chain()

    return jsonify({
        "replaced": replaced,
        "chain_height": len(blockchain.chain) - 1
    })

# ================================
# START SERVER
# ================================

if __name__ == "__main__":

    print("===================================")
    print("BRVX NODE STARTING")
    print("PORT:", PORT)
    print("PEERS:", INITIAL_PEERS)
    print("===================================")

    app.run(host=HOST, port=PORT, debug=False)
