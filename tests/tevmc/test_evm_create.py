#!/usr/bin/env python3

from py_eosio.sugar import random_string


def test_cleos_evm_create(tevmc):
    """Create a random account and have it create a random evm account,
    then wait for hyperion to index the transaction.
    Finally get account action history and verify `eosio.evm::create` is
    present.
    """

    account = tevmc.cleos.new_account()
    
    ec, out = tevmc.cleos.create_evm_account(
        account, random_string())

    tx_id = out['transaction_id']

    assert ec == 0

    tevmc.cleos.hyperion_await_tx(tx_id) 

    account_action_history = tevmc.cleos.hyperion_get_actions(
        account=account)

    tx_ids = [
        tx['trx_id'] for tx in account_action_history['actions']
    ]

    assert tx_id in tx_ids
