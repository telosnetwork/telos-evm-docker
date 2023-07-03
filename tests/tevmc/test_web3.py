#!/usr/bin/env python3

from eth_account import Account

from leap.sugar import random_string, Asset
from leap.tokens import tlos_token

from tevmc.utils import to_wei


DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21000


def test_connect(local_w3):
    assert local_w3.is_connected()


def test_gas_price(tevmc_local, local_w3):
    gas_price = local_w3.eth.gas_price
    tevmc_local.logger.info(gas_price)
    assert gas_price <= 120000000000


def test_chain_id(tevmc_local, local_w3):
    chain_id = tevmc_local.config['telos-evm-rpc']['chain_id']
    assert local_w3.eth.chain_id == chain_id


def test_block_number(tevmc_local, local_w3):
    assert (local_w3.eth.block_number - tevmc_local.cleos.get_info()[
        'head_block_num']) < 10


def test_transaction_count(tevmc_local, local_w3):
    tevmc = tevmc_local

    account = tevmc.cleos.new_account()

    ec, out = tevmc.cleos.create_evm_account(
        account, random_string())
    assert ec == 0

    eth_addr = tevmc.cleos.eth_account_from_name(account)
    assert eth_addr

    quantity = Asset(100, tevmc.cleos.sys_token_supply.symbol)

    tevmc.cleos.transfer_token('eosio', account, quantity, 'evm test')
    tevmc.cleos.transfer_token(account, 'eosio.evm', quantity, 'Deposit')

    assert local_w3.eth.get_transaction_count(
        local_w3.to_checksum_address(eth_addr)) == 1


def test_get_transaction_receipt(
    tevmc_local, local_w3, erc20_deployment
):
    tevmc = tevmc_local

    # create account and register linked evm addr
    account = tevmc.cleos.new_account()

    ec, _ = tevmc.cleos.create_evm_account(
        account, random_string())
    assert ec == 0

    native_eth_addr = tevmc.cleos.eth_account_from_name(account)

    # generate evm addresse with private keys
    first_addr = Account.create()
    second_addr = Account.create()

    tevmc.cleos.transfer_token(
        'eosio', account,
        Asset(100, tlos_token),
        'evm test'
    )
    tevmc.cleos.transfer_token(
        account, 'eosio.evm',
        Asset(100, tlos_token),
        'Deposit'
    )

    ec, _ = tevmc.cleos.eth_transfer(
        account, native_eth_addr, first_addr.address, Asset(90, tlos_token))
    assert ec == 0

    quantity = local_w3.eth.get_balance(first_addr.address) - to_wei(2, 'ether')
    signed_tx = Account.sign_transaction({
        'from': first_addr.address,
        'to': second_addr.address,
        'gas': DEFAULT_GAS,
        'gasPrice': DEFAULT_GAS_PRICE,
        'value': quantity,
        'data': b'',
        'nonce': 0,
        'chainId': tevmc.cleos.chain_id
    }, first_addr.key)


    tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    receipt = local_w3.eth.wait_for_transaction_receipt(tx_hash)
    assert receipt
