class UTXO:
    def __init__(self, txid, output_index, recipient, amount):
        self.txid = txid
        self.output_index = output_index
        self.recipient = recipient
        self.amount = amount

    def to_dict(self):
        return {
            "txid": self.txid,
            "output_index": self.output_index,
            "recipient": self.recipient,
            "amount": self.amount
        }

    @property
    def utxo_id(self):
        return f"{self.txid}:{self.output_index}"
