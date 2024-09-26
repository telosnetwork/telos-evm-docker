#!/usr/bin/env python3

from eth_account import Account

from leap.sugar import random_string
from leap.protocol import Asset
from tevmc.testing import open_web3

from tevmc.utils import to_wei


DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21572

def register_block_producers(tevmc, amount):
    producers = ['eosio']
    tevmc.cleos.register_producer('eosio')

    for i in range(1,amount):
        bp_account = tevmc.cleos.new_account(name=f'produceracc{i}', key=tevmc.cleos.keys['eosio'])
        tevmc.cleos.transfer_token('eosio', bp_account, Asset.from_str('1000000.0000 TLOS'), '21 bp funds')
        tevmc.cleos.register_producer(bp_account, key=tevmc.cleos.keys['eosio'])
        producers.append(bp_account)

    producers.sort()

    for prod in producers:
        if prod == 'eosio':
            continue
        tevmc.cleos.rex_deposit(prod, '1000000.0000 TLOS')
        tevmc.cleos.vote_producers(prod, '', producers)

    tevmc.cleos.wait_block(1000)

def test_generate_fully_tested_chain(tevmc_local):
    tevmc = tevmc_local
    local_w3 = open_web3(tevmc)

    register_block_producers(tevmc, 2)

    # Set max_tx_time to 199ms
    params = {
        "max_block_net_usage": 1048576,
        "target_block_net_usage_pct": 1000,
        "max_transaction_net_usage": 600000,
        "base_per_transaction_net_usage": 12,
        "net_usage_leeway": 500,
        "context_free_discount_net_usage_num": 20,
        "context_free_discount_net_usage_den": 100,
        "max_block_cpu_usage": 200000,
        "target_block_cpu_usage_pct": 500,
        "max_transaction_cpu_usage": 199000,
        "min_transaction_cpu_usage": 100,
        "max_transaction_lifetime": 3600,
        "deferred_trx_expiration_window": 600,
        "max_transaction_delay": 3888000,
        "max_inline_action_size": 524287,
        "max_inline_action_depth": 10,
        "max_authority_depth": 6
    }
    tevmc.cleos.push_action(
        'eosio', 'setparams', [params], 'eosio')
    #breakpoint()

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
        'gas': DEFAULT_GAS * 10,
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
        'gas': DEFAULT_GAS * 10,
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
