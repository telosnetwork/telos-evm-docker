#!/usr/bin/env python3

import pytest

from leap.sugar import Asset

from tevmc.config import local

from web3 import Account


@pytest.mark.randomize(False)
def test_setcode_with_same_hash_subst(nodeos_local):
    tevmc = nodeos_local

    regular_path = '/opt/eosio/bin/contracts/eosio.evm/regular'
    receiptless_path = '/opt/eosio/bin/contracts/eosio.evm/receiptless'

    tevmc.cleos.deploy_contract(
        'eosio.evm', regular_path,
        privileged=True,
        create_account=False,
        verify_hash=False)

    tevmc.cleos.deploy_contract(
        'eosio.evm', receiptless_path,
        privileged=True,
        create_account=False,
        verify_hash=False)

    tevmc.cleos.wait_blocks(10)

    eth_addr = tevmc.cleos.eth_account_from_name('evmuser1')
    assert eth_addr
    ec, _ = tevmc.cleos.eth_transfer(
        'evmuser1',
        eth_addr,
        Account.create().address,
        Asset(1, tevmc.cleos.sys_token_supply.symbol)
    )
    assert ec == 0

    nodeos_logs = tevmc.cleos.wait_for_phrase_in_nodeos_logs(
        'RCPT', lines=5, timeout=4,
        from_file=tevmc.config['nodeos']['log_path']
    )

    assert 'RCPT' in nodeos_logs

