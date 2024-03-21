#!/usr/bin/env python3

from py_eosio.sugar import random_string, collect_stdout, Asset
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

import requests

from web3 import HTTPProvider, Web3
from eth_account import Account

DEFAULT_GAS_PRICE = 1491547668281186
DEFAULT_GAS = 21000

def test_latest_backported_evm_contract(tevmc_local):
    tevmc = tevmc_local
    evm_port = tevmc.config['hyperion']['api']['server_port']
    chain_id = tevmc.config['hyperion']['chain']['chain_id']
    nodeos_http_endpoint = tevmc.config['hyperion']['chain']['http']
    w3 = Web3(HTTPProvider(f'http://127.0.0.1:{evm_port}/evm'))

    # perform get_code to verify we are running old wasm
    resp = requests.post(
        f'{nodeos_http_endpoint}/v1/chain/get_code',
        json={
            'account_name': 'eosio.evm',
            'code_as_wasm': 1
        }).json()

    assert 'code_hash' in resp
    assert resp['code_hash'] == '37a0c1da5c8cf78cfe24b20fea93a41531766dfeef3730d7e1a5ad75bb4ead1a'

    # create native account
    account = tevmc.cleos.new_account()

    # init linked eth address
    ec, _ = tevmc.cleos.create_evm_account(
        account, random_string())
    assert ec == 0

    # get linked addr value
    linked_eth_addr = tevmc.cleos.eth_account_from_name(account)
    assert linked_eth_addr

    # create two ethereum addresses with private keys
    native_eth_addr = Account.create()
    native_eth_addr_second = Account.create()

    # transfer 20,000.0000 TLOS to the linked eth addr
    native_quantity = Asset(20000, sys_token)
    quantity = Asset(20000, sys_token)

    tevmc.cleos.transfer_token('eosio', account, native_quantity, 'evm test')
    tevmc.cleos.transfer_token(account, 'eosio.evm', quantity, 'Deposit')

    tevmc.cleos.wait_blocks(4)

    # confirm balance arrived
    balance = tevmc.cleos.eth_get_balance(linked_eth_addr)

    assert balance == to_wei(quantity.amount, 'ether')

    # transfer from linked address to first ethereum addr
    ec, _ = tevmc.cleos.eth_transfer(
        account,
        linked_eth_addr,
        native_eth_addr.address,
        Asset(1000, sys_token)
    )
    assert ec == 0

    # transfer from first eth addr to second using a regular signed tx
    from_addr = native_eth_addr.address
    to_addr = native_eth_addr_second.address
    quantity = to_wei(5, 'ether')

    signed_tx = Account.sign_transaction({
        'from': from_addr,
        'to': to_addr,
        'gas': DEFAULT_GAS,
        'gasPrice': DEFAULT_GAS_PRICE,
        'value': quantity,
        'data': b'',
        'nonce': 0,
        'chainId': chain_id
    }, native_eth_addr.key)

    w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    tevmc.cleos.wait_blocks(1)

    # verify balance makes sense
    on_chain_balance = tevmc.cleos.eth_get_balance(native_eth_addr_second.address)
    assert on_chain_balance == to_wei(5, 'ether')

    # deploy latest evm contract
    contract_path = '/opt/eosio/bin/contracts/eosio.evm-v2'

    tevmc.cleos.deploy_contract(
        'eosio.evm', contract_path,
        privileged=True,
        create_account=False,
        verify_hash=False)

    tevmc.cleos.wait_blocks(4)

    # verify we are running new wasm
    resp = requests.post(
        f'{nodeos_http_endpoint}/v1/chain/get_code',
        json={
            'account_name': 'eosio.evm',
            'code_as_wasm': 1
        }).json()

    assert 'code_hash' in resp
    assert resp['code_hash'] == 'ab297836a718f08d91e0270d74f11c2e9233b132d90123d558f48594639aa49a'

    # perform a second transfer from first eth addr to second
    from_addr = native_eth_addr.address
    to_addr = native_eth_addr_second.address
    quantity = to_wei(5, 'ether')

    signed_tx = Account.sign_transaction({
        'from': from_addr,
        'to': to_addr,
        'gas': DEFAULT_GAS,
        'gasPrice': DEFAULT_GAS_PRICE,
        'value': quantity,
        'data': b'',
        'nonce': 1,
        'chainId': chain_id
    }, native_eth_addr.key)

    w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    tevmc.cleos.wait_blocks(1)

    # verify balance makes sense
    on_chain_balance = tevmc.cleos.eth_get_balance(native_eth_addr_second.address)
    assert on_chain_balance == to_wei(10, 'ether')


    # increment revision
    ec, _ = self.push_action(
        'eosio.evm',
        'setrevision',
        [1],
        'eosio.evm@active'
    )
    assert ec == 0

    # perform a third transfer
    from_addr = native_eth_addr.address
    to_addr = native_eth_addr_second.address
    quantity = to_wei(5, 'ether')

    signed_tx = Account.sign_transaction({
        'from': from_addr,
        'to': to_addr,
        'gas': DEFAULT_GAS,
        'gasPrice': DEFAULT_GAS_PRICE,
        'value': quantity,
        'data': b'',
        'nonce': 2,
        'chainId': chain_id
    }, native_eth_addr.key)

    w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    tevmc.cleos.wait_blocks(1)

    # verify balance makes sense
    on_chain_balance = tevmc.cleos.eth_get_balance(native_eth_addr_second.address)
    assert on_chain_balance == to_wei(15, 'ether')
