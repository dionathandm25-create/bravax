import hashlib
import json
from ecdsa import VerifyingKey, SECP256k1, BadSignatureError

from core.block import Block
from core.config import (
    DEFAULT_DIFFICULTY,
    GENESIS_DIFFICULTY,
    INITIAL_BLOCK_REWARD,
    HALVING_INTERVAL,
    MAX_SUPPLY,
    PREMINE_FOUNDER,
    PREMINE_DEV,
    PREMINE_MARKETING,
    PREMINE_TOTAL,
    MINING_ALLOCATION
)
from core.transaction import Transaction, TransactionInput, TransactionOutput
from core.utxo import UTXO
from core.storage import load_blockchain_data, rebuild_chain, save_blockchain


class Blockchain:
    def __init__(self):
        self.pending_transactions = []
        self.difficulty = DEFAULT_DIFFICULTY
        self.total_mined = 0
        self.utxo_set = {}
        self.max_transactions_per_block = 5
        self.premine_done = False

        loaded = load_blockchain_data()

        if loaded:
            self.chain = rebuild_chain(loaded["chain"])
            self.difficulty = loaded.get("difficulty", DEFAULT_DIFFICULTY)
            self.total_mined = loaded.get("total_mined", 0)
            self.premine_done = loaded.get("premine_done", False)

            if not self.validate_chain():
                raise ValueError("Blockchain carregada está corrompida ou inválida.")

            print("Blockchain carregada do arquivo e validada com sucesso.")
            self.rebuild_utxo_from_chain()
            self.pending_transactions = self.rebuild_pending_transactions(
                loaded.get("pending_transactions", [])
            )
        else:
            self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        genesis = Block(
            index=0,
            previous_hash="0" * 64,
            transactions=[{
                "type": "genesis",
                "message": "Genesis Block - BRVX Main Chain Start"
            }],
            difficulty=GENESIS_DIFFICULTY
        )
        genesis_hash = genesis.mine_block()
        print(f"Genesis minerado: {genesis_hash}")
        return genesis

    def rebuild_pending_transactions(self, pending_data):
        rebuilt = []

        for tx_data in pending_data:
            inputs = [
                TransactionInput(
                    txid=inp["txid"],
                    output_index=inp["output_index"],
                    signature=inp.get("signature"),
                    public_key=inp.get("public_key")
                )
                for inp in tx_data.get("inputs", [])
            ]

            outputs = [
                TransactionOutput(
                    recipient=out["recipient"],
                    amount=out["amount"]
                )
                for out in tx_data.get("outputs", [])
            ]

            tx = Transaction(
                inputs=inputs,
                outputs=outputs,
                tx_type=tx_data.get("tx_type", "transfer"),
                timestamp=tx_data.get("timestamp"),
                nonce=tx_data.get("nonce")
            )
            rebuilt.append(tx)

        return rebuilt

    def get_latest_block(self):
        return self.chain[-1]

    def get_block_reward(self, block_height):
        halvings = block_height // HALVING_INTERVAL
        reward = INITIAL_BLOCK_REWARD // (2 ** halvings)

        if reward < 1:
            reward = 0

        return reward

    def public_key_to_address(self, public_key_hex):
        public_key_bytes = bytes.fromhex(public_key_hex)
        sha = hashlib.sha256(public_key_bytes).hexdigest()
        return "BRVX" + sha[:32]

    def verify_transaction_signature(self, transaction):
        if transaction.tx_type in ("coinbase", "premine"):
            return True

        signable_hash = transaction.get_signable_hash()

        for tx_input in transaction.inputs:
            if not tx_input.signature or not tx_input.public_key:
                print("Input sem assinatura ou chave pública")
                return False

            try:
                vk = VerifyingKey.from_string(
                    bytes.fromhex(tx_input.public_key),
                    curve=SECP256k1
                )

                vk.verify(
                    bytes.fromhex(tx_input.signature),
                    bytes.fromhex(signable_hash)
                )
            except BadSignatureError:
                print("Assinatura inválida")
                return False
            except Exception as e:
                print(f"Erro ao verificar assinatura: {e}")
                return False

        return True

    def add_transaction(self, transaction):
        if not isinstance(transaction, Transaction):
            raise ValueError("A transação precisa ser um objeto Transaction")

        if transaction.tx_type not in ("coinbase", "premine"):
            if not self.verify_transaction_signature(transaction):
                raise ValueError("Assinatura da transação inválida")

            if not self.validate_transaction(transaction):
                raise ValueError("Transação inválida")

        self.pending_transactions.append(transaction)
        print(f"Transação adicionada à mempool. Total pendente: {len(self.pending_transactions)}")

    def validate_transaction(self, transaction):
        input_total = 0
        output_total = 0

        for tx_input in transaction.inputs:
            utxo_id = f"{tx_input.txid}:{tx_input.output_index}"
            utxo = self.utxo_set.get(utxo_id)

            if utxo is None:
                print(f"UTXO não encontrado: {utxo_id}")
                return False

            derived_address = self.public_key_to_address(tx_input.public_key)
            if utxo.recipient != derived_address:
                print("A chave pública não corresponde ao dono do UTXO")
                return False

            input_total += utxo.amount

        for tx_output in transaction.outputs:
            if tx_output.amount <= 0:
                print("Saída com valor inválido")
                return False
            output_total += tx_output.amount

        if input_total < output_total:
            print("Saldo insuficiente na transação")
            return False

        return True

    def apply_transaction(self, transaction):
        if transaction.tx_type not in ("coinbase", "premine"):
            for tx_input in transaction.inputs:
                utxo_id = f"{tx_input.txid}:{tx_input.output_index}"
                if utxo_id in self.utxo_set:
                    del self.utxo_set[utxo_id]

        for index, tx_output in enumerate(transaction.outputs):
            utxo = UTXO(
                txid=transaction.txid,
                output_index=index,
                recipient=tx_output.recipient,
                amount=tx_output.amount
            )
            self.utxo_set[utxo.utxo_id] = utxo

    def initialize_premine(self, founder_address, dev_address, marketing_address):
        if self.premine_done:
            print("Premine já foi realizado.")
            return False

        if len(self.chain) != 1:
            print("Premine só pode ser feito logo após o bloco gênesis.")
            return False

        premine_tx = Transaction(
            inputs=[],
            outputs=[
                TransactionOutput(founder_address, PREMINE_FOUNDER),
                TransactionOutput(dev_address, PREMINE_DEV),
                TransactionOutput(marketing_address, PREMINE_MARKETING),
            ],
            tx_type="premine"
        )

        block_height = len(self.chain)

        new_block = Block(
            index=block_height,
            previous_hash=self.get_latest_block().calculate_hash(),
            transactions=[premine_tx.to_dict()],
            difficulty=self.difficulty
        )

        mined_hash = new_block.mine_block()
        self.chain.append(new_block)
        self.apply_transaction(premine_tx)

        self.total_mined += PREMINE_TOTAL
        self.premine_done = True

        save_blockchain(self)

        print(f"Bloco de premine minerado: {mined_hash}")
        print(f"Founder premine: {PREMINE_FOUNDER}")
        print(f"Dev premine: {PREMINE_DEV}")
        print(f"Marketing premine: {PREMINE_MARKETING}")
        print(f"Premine total: {PREMINE_TOTAL}")
        print(f"Total emitido após premine: {self.total_mined}")

        return True

    def get_mined_by_pow(self):
        if not self.premine_done:
            return self.total_mined
        return max(0, self.total_mined - PREMINE_TOTAL)

    def mine_pending_transactions(self, miner_address):
        if len(self.pending_transactions) == 0:
            print("Nenhuma transação pendente. Será minerado apenas o bloco com recompensa.")

        block_height = len(self.chain)
        reward = self.get_block_reward(block_height)

        mined_by_pow = self.get_mined_by_pow()

        if mined_by_pow >= MINING_ALLOCATION:
            reward = 0

        if mined_by_pow + reward > MINING_ALLOCATION:
            reward = MINING_ALLOCATION - mined_by_pow

        if self.total_mined + reward > MAX_SUPPLY:
            reward = MAX_SUPPLY - self.total_mined

        selected_transactions = self.pending_transactions[:self.max_transactions_per_block]

        if reward > 0:
            coinbase_tx = Transaction(
                inputs=[],
                outputs=[TransactionOutput(miner_address, reward)],
                tx_type="coinbase"
            )
            selected_transactions.append(coinbase_tx)

        block_transactions = [tx.to_dict() for tx in selected_transactions]

        new_block = Block(
            index=block_height,
            previous_hash=self.get_latest_block().calculate_hash(),
            transactions=block_transactions,
            difficulty=self.difficulty
        )

        mined_hash = new_block.mine_block()
        self.chain.append(new_block)

        for tx in selected_transactions:
            self.apply_transaction(tx)

        mined_non_special = [tx for tx in selected_transactions if tx.tx_type not in ("coinbase", "premine")]
        self.pending_transactions = self.pending_transactions[len(mined_non_special):]

        if reward > 0:
            self.total_mined += reward

        print(f"Bloco minerado: {mined_hash}")
        print(f"Transações mineradas no bloco: {len(selected_transactions)}")
        print(f"Transações restantes na mempool: {len(self.pending_transactions)}")
        print(f"Recompensa do bloco: {reward}")
        print(f"Total emitido: {self.total_mined}")

    def validate_chain(self):
        if not self.chain:
            print("Cadeia vazia")
            return False

        genesis = self.chain[0]
        if genesis.index != 0:
            print("Genesis block inválido: índice incorreto")
            return False

        if genesis.previous_hash != "0" * 64:
            print("Genesis block inválido: previous_hash incorreto")
            return False

        genesis_hash = genesis.calculate_hash()
        if not genesis_hash.startswith("0" * genesis.difficulty):
            print("Genesis block inválido: hash não satisfaz dificuldade")
            return False

        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            if current_block.index != i:
                print(f"Bloco {i} inválido: índice incorreto")
                return False

            if current_block.previous_hash != previous_block.calculate_hash():
                print(f"Bloco {i} inválido: previous_hash não confere")
                return False

            current_hash = current_block.calculate_hash()
            if not current_hash.startswith("0" * current_block.difficulty):
                print(f"Bloco {i} inválido: hash não satisfaz dificuldade")
                return False

        return True

    def calculate_txid_from_dict(self, tx_dict):
        data = {
            "tx_type": tx_dict["tx_type"],
            "timestamp": tx_dict.get("timestamp"),
            "nonce": tx_dict.get("nonce"),
            "inputs": [
                {
                    "txid": i["txid"],
                    "output_index": i["output_index"]
                }
                for i in tx_dict.get("inputs", [])
            ],
            "outputs": tx_dict.get("outputs", [])
        }

        return hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()

    def rebuild_utxo_from_chain(self):
        print("Reconstruindo UTXO set a partir da blockchain...")

        rebuilt_utxo = {}

        for block in self.chain:
            for tx_data in block.transactions:
                if "tx_type" not in tx_data:
                    continue

                tx_type = tx_data["tx_type"]

                if tx_type not in ("coinbase", "premine"):
                    for tx_input in tx_data["inputs"]:
                        utxo_id = f"{tx_input['txid']}:{tx_input['output_index']}"
                        if utxo_id in rebuilt_utxo:
                            del rebuilt_utxo[utxo_id]

                txid = self.calculate_txid_from_dict(tx_data)

                for index, output in enumerate(tx_data["outputs"]):
                    utxo = UTXO(
                        txid=txid,
                        output_index=index,
                        recipient=output["recipient"],
                        amount=output["amount"]
                    )
                    rebuilt_utxo[utxo.utxo_id] = utxo

        self.utxo_set = rebuilt_utxo
        print("UTXO reconstruído com sucesso.")

    def get_total_supply_mined(self):
        return self.total_mined

    def get_balance(self, address):
        balance = 0
        for utxo in self.utxo_set.values():
            if utxo.recipient == address:
                balance += utxo.amount
        return balance

    def get_utxos_for_address(self, address):
        return [utxo for utxo in self.utxo_set.values() if utxo.recipient == address]

    def get_mempool_size(self):
        return len(self.pending_transactions)

    def export_data(self):
        return {
            "chain": [block.to_dict() for block in self.chain],
            "pending_transactions": [tx.to_dict() for tx in self.pending_transactions],
            "difficulty": self.difficulty,
            "total_mined": self.total_mined,
            "premine_done": self.premine_done
        }

    def replace_chain_from_data(self, incoming_data):
        incoming_chain_data = incoming_data.get("chain", [])
        incoming_difficulty = incoming_data.get("difficulty", DEFAULT_DIFFICULTY)
        incoming_total_mined = incoming_data.get("total_mined", 0)
        incoming_pending = incoming_data.get("pending_transactions", [])
        incoming_premine_done = incoming_data.get("premine_done", False)

        if not incoming_chain_data:
            raise ValueError("Cadeia recebida está vazia")

        old_chain = self.chain
        old_difficulty = self.difficulty
        old_total_mined = self.total_mined
        old_pending = self.pending_transactions
        old_premine_done = self.premine_done

        self.chain = rebuild_chain(incoming_chain_data)
        self.difficulty = incoming_difficulty
        self.total_mined = incoming_total_mined
        self.premine_done = incoming_premine_done

        if not self.validate_chain():
            self.chain = old_chain
            self.difficulty = old_difficulty
            self.total_mined = old_total_mined
            self.pending_transactions = old_pending
            self.premine_done = old_premine_done
            raise ValueError("Cadeia recebida é inválida")

        self.rebuild_utxo_from_chain()
        self.pending_transactions = self.rebuild_pending_transactions(incoming_pending)
        save_blockchain(self)

    def replace_with_longer_chain(self, incoming_data):
        incoming_length = len(incoming_data.get("chain", []))
        local_length = len(self.chain)

        if incoming_length > local_length:
            self.replace_chain_from_data(incoming_data)
            return True

        return False
