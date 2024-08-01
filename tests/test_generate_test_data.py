#!/usr/bin/env python3

from eth_account import Account

from leap.sugar import random_string
from leap.protocol import Asset
from tevmc.testing import open_web3

from tevmc.utils import to_wei


DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21000


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
    tevmc.cleos.transfer_token('eosio', account, Asset.from_str('100.0000 TLOS'), 'evm test')

    # Deposit tokens into evm test account
    tevmc.cleos.transfer_token(account, 'eosio.evm', Asset.from_str('100.0000 TLOS'), 'Deposit')

    # Withdraw tokens from evm test account
    tevmc.cleos.eth_withdraw('1.0000 TLOS', account)

    # Perform nativly signed transfer
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

    # Send eth signed tx
    signed_tx = Account.sign_transaction(tx_params, first_addr.key)
    tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    def deploy_new_erc20(name: str, symbol: str, supply: int):
        return tevmc.cleos.eth_deploy_contract_from_files(
            'tests/evm-contracts/ERC20/TestERC20.abi',
            'tests/evm-contracts/ERC20/TestERC20.bin',
            name,
            constructor_arguments=[name, symbol, supply]
        )

    # test erc20 contract deploy
    supply = to_wei(69, 'ether')
    name = 'TestToken'
    symbol = 'TT'
    erc20_contract = deploy_new_erc20(name, symbol, supply)


    # send EIP1559 tx
    maxPriorityFeeGas = local_w3.eth.max_priority_fee
    tx_params = {
        'from': first_addr.address,
        'to': second_addr.address,
        'value': to_wei(1, 'ether'),
        'gas': DEFAULT_GAS,
        'maxFeePerGas': 113378400388,
        'maxPriorityFeePerGas': maxPriorityFeeGas,
        'nonce': 1,
        'chainId': tevmc.cleos.chain_id,
        'type': 2
    }

    # test actuall tx send & fetch receipt
    signed_tx = Account.sign_transaction(tx_params, first_addr.key)
    tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
