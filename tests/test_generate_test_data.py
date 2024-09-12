#!/usr/bin/env python3

from eth_account import Account

from leap.sugar import random_string
from leap.protocol import Asset
from tevmc.testing import open_web3

from tevmc.utils import to_wei


DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21572


def test_generate_fully_tested_chain(tevmc_local):
    tevmc = tevmc_local
    local_w3 = open_web3(tevmc)

    # Generate one new random native address
    account = tevmc.cleos.new_account(name='evmuser')

    # Generate paired eth address
    tevmc.cleos.create_evm_account(account, random_string())
    native_eth_addr = tevmc.cleos.eth_account_from_name(account)

    # Generate two regular eth address
    first_addr = Account.create()
    second_addr = Account.create()

    # Give tokens from system to test account
    tevmc.cleos.transfer_token('eosio', account, Asset.from_str('101000000.0000 TLOS'), 'evm test')

    # Deposit tokens into evm test account
    tevmc.cleos.transfer_token(account, 'eosio.evm', Asset.from_str('101000000.0000 TLOS'), 'Deposit')

    # Withdraw tokens from evm test account
    tevmc.cleos.eth_withdraw('1.0000 TLOS', account)

    # Perform nativly signed transfer
    tevmc.cleos.eth_transfer(native_eth_addr, first_addr.address, Asset.from_str('10000000.0000 TLOS'), account=account)

    quantity = 80085
    tx_params = {
        'from': first_addr.address,
        'to': second_addr.address,
        'gas': DEFAULT_GAS,
        'gasPrice': DEFAULT_GAS_PRICE,
        'value': quantity,
        'data': b'',
        'nonce': 0,
        'chainId': tevmc.cleos.chain_id
    }

    # Send eth signed tx
    signed_tx = Account.sign_transaction(tx_params, first_addr.key)
    tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    # Update rev
    tevmc.cleos.push_action(
        'eosio.evm', 'setrevision', [1], 'eosio.evm')

    # test erc20 contract deploy
    name = 'TestToken'
    symbol = 'TT'
    erc20_contract = tevmc.cleos.eth_deploy_contract_from_files(
        'tests/evm-contracts/ERC20/TestERC20.abi',
        'tests/evm-contracts/ERC20/TestERC20.bin',
        name,
        constructor_arguments=[
            first_addr.address,
            name,
            symbol
        ]
    )

    # Do ERC20 eth signed mint & transfer

    # Mint
    tx_args = {
        'from': first_addr.address,
        'gas': to_wei(0.1, 'telos'),
        'gasPrice': DEFAULT_GAS_PRICE,
        'nonce': 1,
        'chainId': tevmc.cleos.chain_id
    }
    erc20_tx = erc20_contract.functions.mint(
        first_addr.address,
        100
    ).build_transaction(tx_args)
    signed_tx = Account.sign_transaction(erc20_tx, first_addr.key)
    tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    # Transfer
    tx_args = {
        'gas': to_wei(0.1, 'telos'),
        'gasPrice': DEFAULT_GAS_PRICE,
        'nonce': 2,
        'chainId': tevmc.cleos.chain_id
    }
    erc20_tx = erc20_contract.functions.transfer(
        second_addr.address,
        100
    ).build_transaction(tx_args)
    signed_tx = Account.sign_transaction(erc20_tx, first_addr.key)
    tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    # tevmc.cleos.push_action(
    #     'eosio.evm', 'setrevision', [2], 'eosio.evm')

    # # send EIP1559 tx
    # maxPriorityFeeGas = local_w3.eth.max_priority_fee
    # tx_params = {
    #     'from': first_addr.address,
    #     'to': second_addr.address,
    #     'value': to_wei(1, 'ether'),
    #     'gas': DEFAULT_GAS,
    #     'maxFeePerGas': 113378400388,
    #     'maxPriorityFeePerGas': maxPriorityFeeGas,
    #     'nonce': 3,
    #     'chainId': tevmc.cleos.chain_id,
    #     'type': 2
    # }

    # # test actuall tx send & fetch receipt
    # signed_tx = Account.sign_transaction(tx_params, first_addr.key)
    # tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    tevmc.cleos.wait_blocks(1)
