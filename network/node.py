import requests


class PeerNode:
    def __init__(self, blockchain, host, port, peers=None):
        self.blockchain = blockchain
        self.host = host
        self.port = port
        self.peers = set(peers or [])

    @property
    def my_url(self):
        return f"http://{self.host}:{self.port}"

    def register_peer(self, peer_url):
        if not peer_url or peer_url == self.my_url:
            return False

        self.peers.add(peer_url.rstrip("/"))
        return True

    def get_peers(self):
        return sorted(list(self.peers))

    def broadcast_transaction(self, transaction):
        tx_data = transaction.to_dict()
        results = []

        for peer in self.peers:
            try:
                response = requests.post(
                    f"{peer}/node/transaction",
                    json={"transaction": tx_data},
                    timeout=5
                )
                results.append({
                    "peer": peer,
                    "status_code": response.status_code
                })
            except Exception as e:
                results.append({
                    "peer": peer,
                    "error": str(e)
                })

        return results

    def broadcast_chain(self):
        chain_data = self.blockchain.export_data()
        results = []

        for peer in self.peers:
            try:
                response = requests.post(
                    f"{peer}/node/push-chain",
                    json={"blockchain": chain_data},
                    timeout=8
                )
                results.append({
                    "peer": peer,
                    "status_code": response.status_code
                })
            except Exception as e:
                results.append({
                    "peer": peer,
                    "error": str(e)
                })

        return results

    def sync_with_peers(self):
        replaced = False

        for peer in self.peers:
            try:
                response = requests.get(f"{peer}/node/chain", timeout=8)
                if response.status_code != 200:
                    continue

                incoming_data = response.json()
                was_replaced = self.blockchain.replace_with_longer_chain(incoming_data)
                if was_replaced:
                    replaced = True
            except Exception:
                pass

        return replaced
