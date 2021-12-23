#!/usr/bin/env python3

from py_eosio.sugar import random_string, collect_stdout


def test_cleos_evm_create(tevmc):
    """Create a random account and have it create a random evm account,
    then wait for hyperion to index the transaction.
    Finally get account action history and verify `eosio.evm::create` is
    present.
    """

    account = tevmc.cleos.new_account()
    
    ec, out = tevmc.cleos.create_evm_account(
        account, random_string())

    tx_hash = collect_stdout(out)

    assert ec == 0

    tevmc.cleos.hyperion_await_evm_tx(tx_hash) 

    account_action_history = tevmc.cleos.hyperion_get_actions(
        account=account)

    tx_ids = [
        tx['trx_id'] for tx in account_action_history['actions']
    ]

    assert tx_id in tx_ids
