#!/usr/bin/env python3

from py_eosio.sugar import random_string, Asset
from py_eosio.tokens import sys_token


def test_connect(local_w3):
    assert local_w3.is_connected()


def test_gas_price(tevmc_local, local_w3):
    gas_price = local_w3.eth.gas_price
    tevmc_local.logger.info(gas_price)
    assert gas_price <= 120000000000


def test_chain_id(tevmc_local, local_w3):
    chain_id = tevmc_local.config['hyperion']['chain']['chain_id']
    assert local_w3.eth.chain_id == chain_id


def test_block_number(tevmc_local, local_w3):
    local_w3.eth.block_number == tevmc_local.cleos.get_info()[
        'last_irreversible_block_num']


def test_transaction_count(tevmc_local, local_w3):
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

    assert local_w3.eth.get_transaction_count(
        local_w3.to_checksum_address(eth_addr)) == 1
