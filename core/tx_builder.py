from core.transaction import Transaction, TransactionInput, TransactionOutput


def create_transaction(blockchain, sender_wallet, recipient_address, amount):
    utxos = blockchain.get_utxos_for_address(sender_wallet.address)

    selected_utxos = []
    total_collected = 0

    for utxo in utxos:
        selected_utxos.append(utxo)
        total_collected += utxo.amount

        if total_collected >= amount:
            break

    if total_collected < amount:
        raise ValueError("Saldo insuficiente para criar a transação")

    inputs = [
        TransactionInput(utxo.txid, utxo.output_index)
        for utxo in selected_utxos
    ]

    outputs = [TransactionOutput(recipient_address, amount)]

    change = total_collected - amount
    if change > 0:
        outputs.append(TransactionOutput(sender_wallet.address, change))

    tx = Transaction(inputs=inputs, outputs=outputs, tx_type="transfer")

    signable_hash = tx.get_signable_hash()
    signature = sender_wallet.sign_message(signable_hash)

    for tx_input in tx.inputs:
        tx_input.signature = signature
        tx_input.public_key = sender_wallet.public_key

    return tx
