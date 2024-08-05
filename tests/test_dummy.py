#!/usr/bin/env python3

from eth_account import Account

from leap.sugar import random_string
from leap.protocol import Asset
from tevmc.testing import open_web3

from tevmc.utils import to_wei


DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21000


def test_dummy(tevmc_local):
    tevmc = tevmc_local
    local_w3 = open_web3(tevmc)

    # Test get transaction receipt
    account = tevmc.cleos.new_account()
    tevmc.cleos.create_evm_account(account, random_string())
    native_eth_addr = tevmc.cleos.eth_account_from_name(account)
    first_addr = Account.create()
    tevmc.cleos.transfer_token('eosio', account, Asset.from_str('101000000.0000 TLOS'), 'evm test')
    tevmc.cleos.transfer_token(account, 'eosio.evm', Asset.from_str('101000000.0000 TLOS'), 'Deposit')
    tevmc.cleos.eth_transfer(native_eth_addr, first_addr.address, Asset.from_str('10000000.0000 TLOS'), account=account)

    dummy_contract= tevmc.cleos.eth_deploy_contract_from_files(
        'tests/evm-contracts/DummyContract/DummyContract.abi',
        'tests/evm-contracts/DummyContract/DummyContract.bin',
        'DummyContract',
        constructor_arguments=[]
    )

    # call set number
    tx_args = {
        'from': first_addr.address,
        'gas': to_wei(0.1, 'telos'),
        'gasPrice': DEFAULT_GAS_PRICE,
        'nonce': 0,
        'chainId': tevmc.cleos.chain_id
    }
    dummy_tx = dummy_contract.functions.setNumber(
        2001
    ).build_transaction(tx_args)
    signed_tx = Account.sign_transaction(dummy_tx, first_addr.key)
    tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
