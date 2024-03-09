#!/usr/bin/env python3

from leap.sugar import random_string
from leap.protocol import Asset

from tevmc.utils import to_wei
from tevmc.testing import open_web3


def test_cleos_evm_create(tevmc_local):
    """Create a random account and have it create a random evm account,
    then get its ethereum address.
    Send some TLOS and verify in the ethereum side the balance gets added.
    """
    tevmc = tevmc_local
    local_w3 = open_web3(tevmc)

    account = tevmc.cleos.new_account()

    tevmc.cleos.create_evm_account(
        account, random_string())

    eth_addr = tevmc.cleos.eth_account_from_name(account)
    assert eth_addr

    quantity = Asset.from_str('100.0000 TLOS')

    tevmc.cleos.transfer_token('eosio', account, quantity, 'evm test')
    tevmc.cleos.transfer_token(account, 'eosio.evm', quantity, 'Deposit')

    # get balance by checking telos.evm table
    balance = tevmc.cleos.eth_get_balance(eth_addr)

    assert balance == to_wei(quantity.amount // (10 ** quantity.symbol.precision), 'ether')

    # get balance by hitting evm rpc api
    rpc_balance = local_w3.eth.get_balance(
        local_w3.to_checksum_address(eth_addr))

    assert balance == rpc_balance

    # test getblockbynumber call with latest as param
    latest = local_w3.eth.get_block('latest')
    assert latest.number > 0
