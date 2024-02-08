#!/usr/bin/env python3

import pytest

from leap.protocol import Asset

from web3 import Account


@pytest.mark.randomize(False)
@pytest.mark.services('nodeos')
def test_setcode_with_same_hash_subst(tevmc_local):
    tevmc = tevmc_local

    eth_addr = tevmc.cleos.eth_account_from_name('evmuser1')
    assert eth_addr

    def transfer_and_verify_receipt_happens():
        tevmc.cleos.wait_blocks(1)
        ec, _ = tevmc.cleos.eth_transfer(
            eth_addr,
            Account.create().address,
            '1.0000 TLOS',
            account='evmuser1'
        )
        assert ec == 0

        nodeos_logs = ''
        for msg in tevmc.stream_logs('nodeos', num=3, from_latest=True):
            nodeos_logs += msg
            if 'RCPT' in nodeos_logs:
                break

    # at this point blockchain is running with receiptless on chain
    # and using subst to apply regular

    regular_dir = (
        tevmc.docker_wd /
        'leap/contracts/eosio.evm/regular'
    )
    receiptless_dir = (
        tevmc.docker_wd /
        'leap/contracts/eosio.evm/receiptless'
    )

    tevmc.cleos.deploy_contract_from_path(
        'eosio.evm',
        regular_dir,
        privileged=True,
        create_account=False,
        verify_hash=False
    )

    transfer_and_verify_receipt_happens()

    tevmc.cleos.deploy_contract_from_path(
        'eosio.evm',
        receiptless_dir,
        privileged=True,
        create_account=False,
        verify_hash=False
    )

    transfer_and_verify_receipt_happens()


    tevmc.cleos.deploy_contract_from_path(
        'eosio.evm',
        regular_dir,
        privileged=True,
        create_account=False,
        verify_hash=False
    )

    transfer_and_verify_receipt_happens()

    tevmc.cleos.deploy_contract_from_path(
        'eosio.evm',
        receiptless_dir,
        privileged=True,
        create_account=False,
        verify_hash=False
    )

    tevmc.cleos.deploy_contract_from_path(
        'eosio.evm',
        regular_dir,
        privileged=True,
        create_account=False,
        verify_hash=False
    )

    tevmc.cleos.deploy_contract_from_path(
        'eosio.evm',
        receiptless_dir,
        privileged=True,
        create_account=False,
        verify_hash=False
    )

    transfer_and_verify_receipt_happens()
