import hashlib
from ecdsa import SigningKey, SECP256k1


class Wallet:
    def __init__(self, private_key_hex=None):
        if private_key_hex:
            self.signing_key = SigningKey.from_string(
                bytes.fromhex(private_key_hex),
                curve=SECP256k1
            )
        else:
            self.signing_key = SigningKey.generate(curve=SECP256k1)

        self.verifying_key = self.signing_key.get_verifying_key()

        self.private_key = self.signing_key.to_string().hex()
        self.public_key = self.verifying_key.to_string().hex()
        self.address = self.generate_address()

    def generate_address(self):
        public_key_bytes = bytes.fromhex(self.public_key)
        sha = hashlib.sha256(public_key_bytes).hexdigest()
        return "BRVX" + sha[:32]

    def sign_message(self, message_hash_hex):
        signature = self.signing_key.sign(bytes.fromhex(message_hash_hex))
        return signature.hex()

    def to_dict(self):
        return {
            "private_key": self.private_key,
            "public_key": self.public_key,
            "address": self.address
        }
