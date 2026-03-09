import sys

from core.blockchain import Blockchain
from core.config import COIN_SYMBOL, DECIMALS
from core.tx_builder import create_transaction
from core.storage import save_blockchain, save_wallets, load_wallets_data
from wallet.wallet import Wallet


def format_amount(amount):
    return amount / (10 ** DECIMALS)


def parse_amount_to_smallest_unit(amount_str):
    return int(float(amount_str) * (10 ** DECIMALS))


def load_wallets():
    data = load_wallets_data()

    if not data:
        print("Nenhuma carteira encontrada. Rode primeiro: python main.py")
        sys.exit(1)

    return {
        "wallet_a": Wallet(private_key_hex=data["wallet_a"]["private_key"]),
        "wallet_b": Wallet(private_key_hex=data["wallet_b"]["private_key"]),
        "miner_wallet": Wallet(private_key_hex=data["miner_wallet"]["private_key"])
    }


def show_help():
    print("""
=== CLI BRVX ===

Comandos disponíveis:

python cli.py wallets
python cli.py balance
python cli.py balance wallet_a
python cli.py balance wallet_b
python cli.py balance miner_wallet
python cli.py utxos wallet_a
python cli.py utxos wallet_b
python cli.py utxos miner_wallet
python cli.py mine
python cli.py send miner_wallet wallet_a 12
python cli.py send wallet_a wallet_b 3
python cli.py status
""")


def get_wallet_by_name(wallets, name):
    wallet = wallets.get(name)
    if not wallet:
        print(f"Carteira '{name}' não encontrada.")
        print("Use: wallet_a, wallet_b ou miner_wallet")
        sys.exit(1)
    return wallet


def command_wallets(wallets):
    print("=== CARTEIRAS ===")
    for name, wallet in wallets.items():
        print(f"{name}: {wallet.address}")


def command_balance(blockchain, wallets, target=None):
    if target:
        wallet = get_wallet_by_name(wallets, target)
        balance = blockchain.get_balance(wallet.address)
        print(f"{target}: {format_amount(balance)} {COIN_SYMBOL}")
        return

    print("=== SALDOS ===")
    for name, wallet in wallets.items():
        balance = blockchain.get_balance(wallet.address)
        print(f"{name}: {format_amount(balance)} {COIN_SYMBOL}")


def command_utxos(blockchain, wallets, target):
    wallet = get_wallet_by_name(wallets, target)
    utxos = blockchain.get_utxos_for_address(wallet.address)

    print(f"=== UTXOS DE {target} ===")
    if not utxos:
        print("Nenhum UTXO encontrado.")
        return

    total = 0
    for utxo in utxos:
        print(utxo.to_dict())
        total += utxo.amount

    print(f"Total em UTXOs: {format_amount(total)} {COIN_SYMBOL}")


def command_mine(blockchain, wallets):
    miner_wallet = wallets["miner_wallet"]

    print("=== MINERANDO BLOCO ===")
    blockchain.mine_pending_transactions(miner_wallet.address)

    save_blockchain(blockchain)
    save_wallets(wallets)

    print("Bloco minerado e blockchain salva com sucesso.")


def command_send(blockchain, wallets, sender_name, recipient_name, amount_str):
    sender_wallet = get_wallet_by_name(wallets, sender_name)
    recipient_wallet = get_wallet_by_name(wallets, recipient_name)

    amount = parse_amount_to_smallest_unit(amount_str)

    print("=== CRIANDO TRANSAÇÃO ===")
    print(f"De: {sender_name}")
    print(f"Para: {recipient_name}")
    print(f"Valor: {amount_str} {COIN_SYMBOL}")

    tx = create_transaction(
        blockchain=blockchain,
        sender_wallet=sender_wallet,
        recipient_address=recipient_wallet.address,
        amount=amount
    )

    blockchain.add_transaction(tx)

    save_blockchain(blockchain)
    save_wallets(wallets)

    print("Transação adicionada à mempool com sucesso.")


def command_status(blockchain, wallets):
    print("=== STATUS DA BRVX ===")
    print(f"Altura da cadeia: {len(blockchain.chain) - 1} blocos")
    print(f"Transações na mempool: {blockchain.get_mempool_size()}")
    print(f"Total minerado: {format_amount(blockchain.get_total_supply_mined())} {COIN_SYMBOL}")
    print()

    command_balance(blockchain, wallets)


def main():
    wallets = load_wallets()
    blockchain = Blockchain()

    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == "wallets":
        command_wallets(wallets)

    elif command == "balance":
        if len(sys.argv) == 3:
            command_balance(blockchain, wallets, sys.argv[2])
        else:
            command_balance(blockchain, wallets)

    elif command == "utxos":
        if len(sys.argv) != 3:
            print("Uso: python cli.py utxos wallet_a")
            return
        command_utxos(blockchain, wallets, sys.argv[2])

    elif command == "mine":
        command_mine(blockchain, wallets)

    elif command == "send":
        if len(sys.argv) != 5:
            print("Uso: python cli.py send miner_wallet wallet_a 12")
            return
        command_send(blockchain, wallets, sys.argv[2], sys.argv[3], sys.argv[4])

    elif command == "status":
        command_status(blockchain, wallets)

    else:
        print("Comando não reconhecido.")
        show_help()


if __name__ == "__main__":
    main()
