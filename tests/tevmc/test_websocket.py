#!/usr/bin/env python3

import time
import json

from leap.sugar import random_string, asset_from_str, Asset
from leap.tokens import tlos_token

from tevmc.utils import to_wei

from eth_account import Account


DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21000


def test_websocket_local_new_heads(tevmc_local):

    tevmc = tevmc_local

    ws = tevmc.open_rpc_websocket()

    # send subscribe packet
    ws.send(json.dumps({
        'id': 1,
        'method': 'eth_subscribe',
        'params': ['newHeads']
    }))

    msg = json.loads(ws.recv())
    tevmc.logger.info(msg)

    assert 'jsonrpc' in msg and msg['jsonrpc'] == '2.0'
    assert 'result' in msg
    assert 'id' in msg and msg['id'] == 1

    msg = json.loads(ws.recv())
    tevmc.logger.info(msg)

    assert 'difficulty' in msg
    assert 'extraData' in msg
    assert 'gasLimit' in msg
    assert 'miner' in msg
    assert 'nonce' in msg
    assert 'parentHash' in msg
    assert 'receiptsRoot' in msg
    assert 'sha3Uncles' in msg
    assert 'stateRoot' in msg
    assert 'transactionsRoot' in msg
    assert 'gasUsed' in msg
    assert 'logsBloom' in msg
    assert 'number' in msg
    assert 'timestamp' in msg


def test_websocket_local_rpc(tevmc_local, local_websocket_w3):
    tevmc = tevmc_local
    ws = local_websocket_w3

    # create native account and deposit tokens to evm linked addr
    account = tevmc.cleos.new_account()
    ec, _ = tevmc.cleos.create_evm_account(
        account, random_string())
    assert ec == 0

    primary = tevmc.cleos.eth_account_from_name(account)

    initial_tokens = Asset(102, tlos_token)
    tevmc.cleos.transfer_token(
        'eosio', account,
        initial_tokens,
        'evm test'
    )
    tevmc.cleos.transfer_token(
        account, 'eosio.evm',
        initial_tokens,
        'Deposit'
    )

    # create real evm account and transfer tokens
    address = Account.create()
    ec, out = tevmc.cleos.eth_transfer(
        account,
        primary,
        address.address,
        Asset(initial_tokens.amount - 1, tlos_token)
    )
    assert ec == 0

    # create secondary account and transfer tokens using ws rpc api
    secondary = Account.create()

    quantity = ws.eth.get_balance(address.address) - to_wei(1, 'ether')

    tx_hash = ws.eth.send_raw_transaction(
        Account.sign_transaction({
            'from': address.address,
            'to': secondary.address,
            'gas': DEFAULT_GAS,
            'gasPrice': DEFAULT_GAS_PRICE,
            'value': quantity,
            'data': b'',
            'nonce': 0,
            'chainId': tevmc.cleos.chain_id
        }, address.key).rawTransaction
    )

    # finally wait for the transaction receipt
    receipt = ws.eth.wait_for_transaction_receipt(tx_hash)

    assert receipt['status'] == 1

def test_websocket_mainnet_new_heads(tevmc_mainnet_no_wait):

    tevmc = tevmc_mainnet_no_wait

    ws = tevmc.open_rpc_websocket()

    # send subscribe packet
    ws.send(json.dumps({
        'id': 1,
        'method': 'eth_subscribe',
        'params': ['newHeads']
    }))

    msg = json.loads(ws.recv())
    tevmc.logger.info(msg)

    assert 'jsonrpc' in msg and msg['jsonrpc'] == '2.0'
    assert 'result' in msg
    assert 'id' in msg and msg['id'] == 1

    msg = json.loads(ws.recv())
    tevmc.logger.info(json.dumps(msg, indent=4))

    assert 'difficulty' in msg
    assert 'extraData' in msg
    assert 'gasLimit' in msg
    assert 'miner' in msg
    assert 'nonce' in msg
    assert 'parentHash' in msg
    assert 'receiptsRoot' in msg
    assert 'sha3Uncles' in msg
    assert 'stateRoot' in msg
    assert 'transactionsRoot' in msg
    assert 'gasUsed' in msg
    assert 'logsBloom' in msg
    assert 'number' in msg
    assert 'timestamp' in msg
