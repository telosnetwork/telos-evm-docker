#!/usr/bin/env python3

from eth_account import Account

from leap.sugar import random_string
from leap.protocol import Asset
from tevmc.testing import open_web3

from tevmc.utils import to_wei


DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21000


def test_all(compile_evm, tevmc_local):
    local_w3 = open_web3(tevmc_local)

    # Test connection
    assert local_w3.is_connected()

    # Test gas price
    gas_price = local_w3.eth.gas_price
    tevmc_local.logger.info(gas_price)
    assert gas_price <= 120000000000

    # Test chain ID
    chain_id = tevmc_local.config['telos-evm-rpc']['chain_id']
    assert local_w3.eth.chain_id == chain_id

    # Test block number
    assert (local_w3.eth.block_number - tevmc_local.cleos.get_info()['head_block_num']) < 10

    # Test transaction count
    tevmc = tevmc_local
    account = tevmc.cleos.new_account()
    tevmc.cleos.create_evm_account(account, random_string())
    eth_addr = tevmc.cleos.eth_account_from_name(account)
    assert eth_addr
    quantity = Asset.from_str('100.0000 TLOS')
    tevmc.cleos.transfer_token('eosio', account, quantity, 'evm test')
    tevmc.cleos.transfer_token(account, 'eosio.evm', quantity, 'Deposit')
    assert local_w3.eth.get_transaction_count(local_w3.to_checksum_address(eth_addr)) == 1

    # Test get transaction receipt
    tevmc = tevmc_local
    account = tevmc.cleos.new_account()
    tevmc.cleos.create_evm_account(account, random_string())
    native_eth_addr = tevmc.cleos.eth_account_from_name(account)
    first_addr = Account.create()
    second_addr = Account.create()
    tevmc.cleos.transfer_token('eosio', account, Asset.from_str('100.0000 TLOS'), 'evm test')
    tevmc.cleos.transfer_token(account, 'eosio.evm', Asset.from_str('100.0000 TLOS'), 'Deposit')
    tevmc.cleos.eth_transfer(native_eth_addr, first_addr.address, Asset.from_str('90.0000 TLOS'), account=account)

    quantity = local_w3.eth.get_balance(first_addr.address) - to_wei(2, 'ether')
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

    # test gas estimation
    gas_est = local_w3.eth.estimate_gas(tx_params)
    assert gas_est == 26250

    # test actuall tx send & fetch receipt
    signed_tx = Account.sign_transaction(tx_params, first_addr.key)
    tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = local_w3.eth.wait_for_transaction_receipt(tx_hash)
    assert receipt

    # test erc20 contract deploy
    total_supply_wei = to_wei(69, 'ether')
    erc20_contract = tevmc_local.cleos.eth_deploy_contract_from_json(
        'tests/evm-contracts/uniswap-v2-core/build/ERC20.json',
        'UniswapV2Token',
        constructor_arguments=[total_supply_wei]
    )
    assert erc20_contract.functions.totalSupply().call() == total_supply_wei
