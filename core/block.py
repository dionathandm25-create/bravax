import hashlib
import json
import time


class Block:
    def __init__(self, index, previous_hash, transactions, timestamp=None, nonce=0, difficulty=4):
        self.index = index
        self.previous_hash = previous_hash
        self.transactions = transactions
        self.timestamp = timestamp if timestamp is not None else int(time.time())
        self.nonce = nonce
        self.difficulty = difficulty

    def to_dict(self):
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "difficulty": self.difficulty
        }

    def calculate_hash(self):
        block_string = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def mine_block(self):
        target = "0" * self.difficulty

        while True:
            block_hash = self.calculate_hash()
            if block_hash.startswith(target):
                return block_hash
            self.nonce += 1
