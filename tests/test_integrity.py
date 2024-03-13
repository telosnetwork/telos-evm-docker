#!/usr/bin/env python3

import time
import random

from eth_account import Account
from elasticsearch import Elasticsearch

from leap.sugar import random_string
from leap.tokens import tlos_token
from leap.protocol import Asset
from tevmc.testing import open_web3

from tevmc.utils import to_wei, to_int, from_wei, decode_hex


DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21000


def test_integrity_elastic(tevmc_local):
    tevmc = tevmc_local
    local_w3 = open_web3(tevmc_local)

    index = tevmc.config['telos-evm-rpc']['elastic_prefix'] + '-action-*'

    es_config = tevmc.config['elasticsearch']
    es = Elasticsearch(
        f'{es_config["protocol"]}://{es_config["host"]}',
        basic_auth=(
            es_config['user'], es_config['pass']
        )
    )

    def get_elastic_balance(addr: str | Account):
        """Query all elasticsearch transactions to and from `addr`, then tally
        up balance and return
        """
        if hasattr(addr, 'address'):
            addr = addr.address

        addr = addr.lower()

        result = es.search(
            index=index,
            query={
                'query_string': {
                    'query': f'@raw.from: \"{addr}\"',
                }
            }
        )
        outgoing = result['hits']['hits']

        result = es.search(
            index=index,
            query={
                'query_string': {
                    'query': f'@raw.to: \"{addr}\"',
                }
            }
        )
        incoming = result['hits']['hits']

        balance_hex = 0

        for transfer in incoming:
            balance_hex += to_int(hexstr=transfer['_source']['@raw']['value'])

        total_payed_in_gas = 0
        for transfer in outgoing:
            balance_hex -= to_int(hexstr=transfer['_source']['@raw']['value'])
            total_payed_in_gas += int(transfer[
                '_source']['@raw']['gasused']) * int(transfer['_source']['@raw']['charged_gas_price'])

        total_payed_in_gas = from_wei(total_payed_in_gas, 'ether')
        balance_hex = from_wei(balance_hex, 'ether')

        return to_wei(float(balance_hex - total_payed_in_gas), 'ether')

    # create $amount native telos accounts and register
    # evm addr for each of them, then generate $amount
    # native EVM addresses

    amount = 10

    # for the math to make sense we need an even amount of accounts
    assert amount % 2 == 0

    # create accounts and register linked evm addr
    accounts = [
        tevmc.cleos.new_account()
        for i in range(amount)
    ]

    for account in accounts:
        ec, _ = tevmc.cleos.create_evm_account(
            account, random_string())
        assert ec == 0

    native_eth_addrs = [
        tevmc.cleos.eth_account_from_name(account)
        for account in accounts
    ]

    # generate evm addresses with private keys
    internal_eth_addrs = [
        Account.create()
        for i in range(amount)
    ]

    # send a random quantity of telos from eosio tokens
    # to the native telos accounts, and then deposit to evm

    initial_deposit_assets = [
        Asset(random.randint(100, 10000), tlos_token)
        for i in range(amount)
    ]

    for i, account in enumerate(accounts):
        tevmc.cleos.transfer_token(
            'eosio', account,
            initial_deposit_assets[i],
            'evm test'
        )
        tevmc.cleos.transfer_token(
            account, 'eosio.evm',
            initial_deposit_assets[i],
            'Deposit'
        )

    time.sleep(2)

    # check acording to eosio.evm table and elastic
    for addr, deposit in zip(native_eth_addrs, initial_deposit_assets):
        assert tevmc.cleos.eth_get_balance(addr) == to_wei(deposit.amount, 'ether')
        assert get_elastic_balance(addr) == to_wei(deposit.amount, 'ether')

    # transfer to native evm accounts
    for account, native_eth_addr, eth_addr, init_deposit_asset in zip(
        accounts,
        native_eth_addrs,
        internal_eth_addrs,
        initial_deposit_assets
    ):
        ec, _ = tevmc.cleos.eth_transfer(
            account,
            native_eth_addr,
            eth_addr.address,
            Asset(init_deposit_asset.amount - 1, tlos_token)
        )
        assert ec == 0

    time.sleep(2)

    for addr, deposit in zip(internal_eth_addrs, initial_deposit_assets):
        on_chain_balance = tevmc.cleos.eth_get_balance(addr.address)
        assert on_chain_balance == to_wei(deposit.amount - 1, 'ether')
        assert on_chain_balance == get_elastic_balance(addr)

    # transfer between native evm accounts
    txs = []
    for i in range(amount):
        from_addr = internal_eth_addrs[i]
        to_addr = internal_eth_addrs[amount - i - 1]
        quantity = local_w3.eth.get_balance(from_addr.address) - to_wei(2, 'ether')

        signed_tx = Account.sign_transaction({
            'from': from_addr.address,
            'to': to_addr.address,
            'gas': DEFAULT_GAS,
            'gasPrice': DEFAULT_GAS_PRICE,
            'value': quantity,
            'data': b'',
            'nonce': 0,
            'chainId': tevmc.cleos.chain_id
        }, from_addr.key)

        txs.append(signed_tx)

    for tx in txs:
        local_w3.eth.send_raw_transaction(tx.rawTransaction)

    # now send funds to evm addresses of native telos accounts
    for i in range(amount):
        from_addr = internal_eth_addrs[i]
        to_addr = decode_hex(native_eth_addrs[i])
        quantity = local_w3.eth.get_balance(from_addr.address) - to_wei(1, 'ether')

        signed_tx = Account.sign_transaction({
            'from': from_addr.address,
            'to': to_addr,
            'gas': DEFAULT_GAS,
            'gasPrice': DEFAULT_GAS_PRICE,
            'value': quantity,
            'data': b'',
            'nonce': 1,
            'chainId': tevmc.cleos.chain_id
        }, from_addr.key)

        local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    # now withdraw back to native
    for account, addr in zip(accounts, native_eth_addrs):
        addr = local_w3.to_checksum_address(addr)
        ec, _ = tevmc.cleos.eth_withdraw(
            account,
            Asset(
                from_wei(local_w3.eth.get_balance(addr), 'ether'),
                tevmc_local.cleos.sys_token_supply.symbol),
            account
        )
        assert ec == 0

    time.sleep(2)

    # check elastic balances of linked address and make sure is less than
    # minimun telos representable
    for addr in native_eth_addrs:
        assert float(from_wei(get_elastic_balance(addr), 'ether')) < 0.0001

    # make sure elastic balance for real evm addresses matches up with evm
    # contract table
    for addr in internal_eth_addrs:
        assert get_elastic_balance(addr) == tevmc.cleos.eth_get_balance(addr.address)

    # make sure balances are inverted on the native side
    for i, account in enumerate(accounts):
        balance = Asset.from_str(tevmc.cleos.get_balance(account))
        asset = initial_deposit_assets[amount - i - 1]

        assert asset.amount - balance.amount < 1.005
