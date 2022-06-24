#!/usr/bin/env python3

from py_eosio.sugar import random_string, Asset
from py_eosio.tokens import sys_token

from tevmc.utils import to_wei


def test_cleos_evm_create(tevmc_local):
    """Create a random account and have it create a random evm account,
    then get its ethereum address.
    Send some TLOS and verify in the ethereum side the balance gets added.
    """
    tevmc = tevmc_local

    account = tevmc.cleos.new_account()
    
    ec, out = tevmc.cleos.create_evm_account(
        account, random_string())
    assert ec == 0

    eth_addr = tevmc.cleos.eth_account_from_name(account)
    assert eth_addr

    quantity = Asset(100, sys_token)

    tevmc.cleos.transfer_token('eosio', account, quantity, 'evm test')
    tevmc.cleos.transfer_token(account, 'eosio.evm', quantity, 'Deposit')

    balance = tevmc.cleos.eth_get_balance(eth_addr)

    assert balance == to_wei(quantity.amount, 'ether')

