#!/usr/bin/env python3

from eth_account import Account

from leap.sugar import random_string
from leap.protocol import Asset
from tevmc.testing import open_web3



DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21000


def test_evm_override_time(compile_evm, tevmc_local):
    tevmc = tevmc_local
    local_w3 = open_web3(tevmc_local)

    account = tevmc.cleos.new_account()
    tevmc.cleos.create_evm_account(account, random_string())
    native_eth_addr = tevmc.cleos.eth_account_from_name(account)
    eth_addr = Account.create()

    tevmc.cleos.transfer_token('eosio', account, Asset.from_str('100.0000 TLOS'), 'evm test')
    tevmc.cleos.transfer_token(account, 'eosio.evm', Asset.from_str('100.0000 TLOS'), 'Deposit')
    tevmc.cleos.eth_transfer(native_eth_addr, eth_addr.address, Asset.from_str('90.0000 TLOS'), account=account)

    evm_mechs = tevmc_local.cleos.eth_deploy_contract_from_json(
        'tests/evm-contracts/evm-mechanics/build/EVMMechanics.json',
        'EVMMechanics',
        account=eth_addr,
        constructor_arguments=[]
    )

    def call_ro_evm(max_prime: int):
        tx_args = {
            'from': eth_addr.address,
            'gas': int(1e8),
            'gasPrice': local_w3.eth.gas_price,
            'nonce': local_w3.eth.get_transaction_count(account=eth_addr.address)
        }

        tx = evm_mechs.functions.roEvm(max_prime).build_transaction(tx_args)
        signed_tx = eth_addr.sign_transaction(tx)
        tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return local_w3.eth.wait_for_transaction_receipt(tx_hash)

    for i in range(1, 21):
        receipt = call_ro_evm(i * 100)
        tevmc.logger.info(f'{receipt["transactionHash"].hex()} success mp == {i * 100}')
