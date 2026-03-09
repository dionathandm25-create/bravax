from core.blockchain import Blockchain
from core.config import COIN_NAME, COIN_SYMBOL, DECIMALS, SMALLEST_UNIT_NAME
from core.tx_builder import create_transaction
from core.storage import save_blockchain, save_wallets, load_wallets_data
from core.transaction import Transaction, TransactionInput, TransactionOutput
from wallet.wallet import Wallet


def format_amount(amount):
    return amount / (10 ** DECIMALS)


def show_balance(blockchain, label, address):
    balance = blockchain.get_balance(address)
    print(f"{label}: {format_amount(balance)} {COIN_SYMBOL}")


def load_or_create_wallets():
    data = load_wallets_data()

    if data:
        print("Carteiras carregadas do arquivo.")
        return {
            "wallet_a": Wallet(private_key_hex=data["wallet_a"]["private_key"]),
            "wallet_b": Wallet(private_key_hex=data["wallet_b"]["private_key"]),
            "miner_wallet": Wallet(private_key_hex=data["miner_wallet"]["private_key"])
        }

    print("Nenhuma carteira salva encontrada. Criando novas carteiras.")
    wallets = {
        "wallet_a": Wallet(),
        "wallet_b": Wallet(),
        "miner_wallet": Wallet()
    }
    save_wallets(wallets)
    return wallets


def test_fake_signature_attack(blockchain, wallet_a, wallet_b):
    print("\n=== TESTE REAL DE FRAUDE DE ASSINATURA ===")

    utxos_a = blockchain.get_utxos_for_address(wallet_a.address)

    if not utxos_a:
        print("Nenhum UTXO encontrado para a Carteira A. Teste não pôde ser executado.")
        return

    target_utxo = utxos_a[0]

    print("UTXO da Carteira A escolhido para teste:")
    print(target_utxo.to_dict())

    fake_input = TransactionInput(
        txid=target_utxo.txid,
        output_index=target_utxo.output_index
    )

    fake_output = TransactionOutput(
        recipient=wallet_b.address,
        amount=target_utxo.amount
    )

    fake_tx = Transaction(
        inputs=[fake_input],
        outputs=[fake_output],
        tx_type="transfer"
    )

    signable_hash = fake_tx.get_signable_hash()
    fake_signature = wallet_b.sign_message(signable_hash)

    fake_tx.inputs[0].signature = fake_signature
    fake_tx.inputs[0].public_key = wallet_b.public_key

    try:
        blockchain.add_transaction(fake_tx)
        print("ERRO: a transação fraudulenta foi aceita e isso não deveria acontecer.")
    except Exception as e:
        print("Sucesso: fraude bloqueada pela BRVX.")
        print("Motivo:", e)


def main():
    print(f"\n=== Iniciando blockchain {COIN_NAME} ({COIN_SYMBOL}) ===\n")

    wallets = load_or_create_wallets()
    wallet_a = wallets["wallet_a"]
    wallet_b = wallets["wallet_b"]
    miner_wallet = wallets["miner_wallet"]

    print("=== CARTEIRAS ===")
    print("Carteira A:", wallet_a.address)
    print("Carteira B:", wallet_b.address)
    print("Carteira Minerador:", miner_wallet.address)

    brvx = Blockchain()

    print("\n=== VALIDAÇÃO DA CADEIA ===")
    if brvx.validate_chain():
        print("Blockchain íntegra e válida.")
    else:
        print("Blockchain inválida.")

    print("\n=== SALDOS ATUAIS ===")
    show_balance(brvx, "Carteira A", wallet_a.address)
    show_balance(brvx, "Carteira B", wallet_b.address)
    show_balance(brvx, "Minerador", miner_wallet.address)

    print(f"\n=== MEMPOOL ATUAL ===")
    print(f"Transações pendentes: {brvx.get_mempool_size()}")

    # PRIMEIRA EXECUÇÃO: minerar primeiro para o minerador ter saldo
    if len(brvx.chain) == 1 and brvx.get_balance(miner_wallet.address) == 0:
        print("\n=== PRIMEIRA EXECUÇÃO DETECTADA ===")
        print("Minerando primeiro bloco de recompensa para o minerador...")
        brvx.mine_pending_transactions(miner_wallet.address)

        save_blockchain(brvx)
        save_wallets(wallets)

        print("\n=== SALDOS APÓS BLOCO INICIAL ===")
        show_balance(brvx, "Carteira A", wallet_a.address)
        show_balance(brvx, "Carteira B", wallet_b.address)
        show_balance(brvx, "Minerador", miner_wallet.address)

    print("\n=== CRIANDO NOVA TRANSAÇÃO: MINERADOR -> CARTEIRA B (5 BRVX) ===")
    tx1 = create_transaction(
        blockchain=brvx,
        sender_wallet=miner_wallet,
        recipient_address=wallet_b.address,
        amount=5 * (10 ** DECIMALS)
    )
    brvx.add_transaction(tx1)

    # Só cria a transação da A se ela tiver saldo suficiente
    if brvx.get_balance(wallet_a.address) >= 2 * (10 ** DECIMALS):
        print("\n=== CRIANDO NOVA TRANSAÇÃO: CARTEIRA A -> CARTEIRA B (2 BRVX) ===")
        tx2 = create_transaction(
            blockchain=brvx,
            sender_wallet=wallet_a,
            recipient_address=wallet_b.address,
            amount=2 * (10 ** DECIMALS)
        )
        brvx.add_transaction(tx2)
    else:
        print("\n=== CARTEIRA A AINDA NÃO TEM SALDO PARA ENVIAR 2 BRVX ===")

    print(f"\n=== MEMPOOL ANTES DA MINERAÇÃO ===")
    print(f"Transações pendentes: {brvx.get_mempool_size()}")

    print("\n=== MINERANDO BLOCO COM TRANSAÇÕES DA MEMPOOL ===")
    brvx.mine_pending_transactions(miner_wallet.address)

    save_blockchain(brvx)
    save_wallets(wallets)

    print(f"\n=== MEMPOOL APÓS MINERAÇÃO ===")
    print(f"Transações pendentes: {brvx.get_mempool_size()}")

    print("\n=== SALDOS APÓS MINERAÇÃO ===")
    show_balance(brvx, "Carteira A", wallet_a.address)
    show_balance(brvx, "Carteira B", wallet_b.address)
    show_balance(brvx, "Minerador", miner_wallet.address)

    test_fake_signature_attack(brvx, wallet_a, wallet_b)

    print("\n=== RESUMO MONETÁRIO ===")
    print(f"Unidade mínima: {SMALLEST_UNIT_NAME}")
    print(f"Casas decimais: {DECIMALS}")
    print(f"Total minerado: {format_amount(brvx.get_total_supply_mined())} {COIN_SYMBOL}")
    print(f"Altura da cadeia: {len(brvx.chain) - 1} blocos")


if __name__ == "__main__":
    main()
