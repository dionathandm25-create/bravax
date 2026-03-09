import hashlib
import json
import time
import secrets


class TransactionInput:
    def __init__(self, txid, output_index, signature=None, public_key=None):
        self.txid = txid
        self.output_index = output_index
        self.signature = signature
        self.public_key = public_key

    def to_dict(self):
        return {
            "txid": self.txid,
            "output_index": self.output_index,
            "signature": self.signature,
            "public_key": self.public_key
        }


class TransactionOutput:
    def __init__(self, recipient, amount):
        self.recipient = recipient
        self.amount = amount

    def to_dict(self):
        return {
            "recipient": self.recipient,
            "amount": self.amount
        }


class Transaction:
    def __init__(self, inputs=None, outputs=None, tx_type="transfer", timestamp=None, nonce=None):
        self.inputs = inputs if inputs is not None else []
        self.outputs = outputs if outputs is not None else []
        self.tx_type = tx_type
        self.timestamp = timestamp if timestamp is not None else int(time.time() * 1000)
        self.nonce = nonce if nonce is not None else secrets.token_hex(8)
        self.txid = self.calculate_txid()

    def to_dict(self):
        return {
            "tx_type": self.tx_type,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "inputs": [tx_input.to_dict() for tx_input in self.inputs],
            "outputs": [tx_output.to_dict() for tx_output in self.outputs]
        }

    def calculate_txid(self):
        tx_string = json.dumps({
            "tx_type": self.tx_type,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "inputs": [
                {
                    "txid": tx_input.txid,
                    "output_index": tx_input.output_index
                }
                for tx_input in self.inputs
            ],
            "outputs": [tx_output.to_dict() for tx_output in self.outputs]
        }, sort_keys=True).encode()

        return hashlib.sha256(tx_string).hexdigest()

    def get_signable_hash(self):
        signable_data = {
            "tx_type": self.tx_type,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "inputs": [
                {
                    "txid": tx_input.txid,
                    "output_index": tx_input.output_index
                }
                for tx_input in self.inputs
            ],
            "outputs": [tx_output.to_dict() for tx_output in self.outputs]
        }

        return hashlib.sha256(
            json.dumps(signable_data, sort_keys=True).encode()
        ).hexdigest()
