#!/usr/bin/env python3

import time
import requests

from typing import Optional, Dict

import simple_rlp as rlp

from py_eosio.cleos import CLEOS
from py_eosio.sugar import Name, Asset
from py_eosio.tokens import sys_token
# from eth_utils import to_wei, to_int, decode_hex, remove_0x_prefix

from .utils import to_wei, to_int, decode_hex, remove_0x_prefix


EVM_CONTRACT = 'eosio.evm'
DEFAULT_GAS_PRICE = '0x01'
DEFAULT_GAS_LIMIT = '0x1e8480'
DEFAULT_VALUE = '0x00'
DEFAULT_DATA = '0x00'


class CLEOSEVM(CLEOS):

    def __init__(
        self,
        *args, 
        hyperion_api_endpoint: str = 'http://127.0.0.1:7000',
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        
        self.hyperion_api_endpoint = hyperion_api_endpoint

        self.__jsonrpc_id = 0
    
    def deploy_evm(
        self,
        start_bytes: int = 1073741824,
        target_free: int = 1073741824,
        min_buy: int = 20000,
        fee_transfer_pct: int = 100,
        gas_per_byte: int = 69
    ):
    
        # create evm accounts
        self.new_account(
            'eosio.evm',
            key='EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L',
            ram=start_bytes)

        self.new_account(
            'fees.evm',
            key='EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L',
            ram=100000)

        ram_price_post = self.get_ram_price()

        start_cost = Asset(ram_price_post.amount * start_bytes, sys_token)

        self.new_account(
            'rpc.evm',
            key='EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L',
            cpu='10000.0000 TLOS',
            net='10000.0000 TLOS',
            ram=100000)

        contract_path = '/opt/eosio/bin/contracts/eosio.evm'

        self.deploy_contract(
            'eosio.evm', contract_path,
            privileged=True,
            create_account=False,
            verify_hash=False)

        ec, out = self.push_action(
            'eosio.evm',
            'init',
            [
                start_bytes,
                start_cost,
                target_free,
                min_buy,
                fee_transfer_pct,
                gas_per_byte
            ], 'eosio.evm@active')
        assert ec == 0

    def create_test_evm_account(
        self,
        name: str = 'evmuser1',
        data: str = 'foobar',
        truffle_addr: str = '0xf79b834a37f3143f4a73fc3934edac67fd3a01cd'
    ):
        self.new_account(
            name,
            key='EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L')
        self.create_evm_account(name, data)
        quantity = Asset(111000000, sys_token)
        
        self.transfer_token('eosio', name, quantity, ' ')
        self.transfer_token(name, 'eosio.evm', quantity, 'Deposit')

        eth_addr = self.eth_account_from_name(name)
        assert eth_addr 

        self.logger.info(f'{name}: {eth_addr}')

        addr_amount_pairs = [
            (truffle_addr, 100000000),
            ('0xc51fE232a0153F1F44572369Cefe7b90f2BA08a5', 100000),
            ('0xf922CC0c6CA8Cdbf5330A295a11A40911FDD3B6e', 10000),
            ('0xCfCf671eBE5880d2D7798d06Ff7fFBa9bdA1bE64', 10000),
            ('0xf6E6c4A9Ca3422C2e4F21859790226DC6179364d', 10000),
            ('0xe83b5B17AfedDb1f6FF08805CE9A4d5eDc547Fa2', 10000),
            ('0x97baF2200Bf3053cc568AA278a55445059dF2d97', 10000),
            ('0x2e5A2c606a5d3244A0E8A4C4541Dfa2Ec0bb0a76', 10000),
            ('0xb4A541e669D73454e37627CdE2229Ad208d19ebF', 10000),
            ('0x717230bA327FE8DF1E61434D99744E4aDeFC53a0', 10000),
            ('0x52b7c04839506427620A2B759c9d729BE0d4d126', 10000)
        ]

        for addr, amount in addr_amount_pairs:
            ec, out = self.eth_transfer(
                'evmuser1',
                eth_addr,
                addr,
                Asset(amount, sys_token)
            )
            time.sleep(0.05)
            assert ec == 0


    """    eosio.evm interaction
    """

    def get_evm_config(self):
        return self.get_table(
            'eosio.evm', 'eosio.evm', 'config')

    def get_evm_resources(self):
        return self.get_table(
            'eosio.evm', 'eosio.evm', 'resources')

    def eth_account_from_name(self, name) -> Optional[str]:
        rows = self.get_table(
            'eosio.evm', 'eosio.evm', 'account',
            '--key-type', 'name', '--index', '3',
            '--lower', name,
            '--upper', name)
        
        if len(rows) != 1:
            return None

        return f'0x{rows[0]["address"]}'

    def create_evm_account(
        self,
        account: str,
        salt: str
    ):
        return self.push_action(
            'eosio.evm',
            'create',
            [account, salt],
            f'{account}@active'
        )

    """    hyperion interaction
    """

    def hyperion_health(self) -> Dict:
        return requests.get(
            f'{self.hyperion_api_endpoint}/v2/health').json()

    # def hyperion_await_evm_tx(self, tx_hash):
    #     while True:
    #         resp = requests.get(
    #             f'{self.hyperion_api_endpoint}/v2/evm/get_transactions',
    #             params={'hash': tx_hash}).json()

    #         breakpoint()

    def hyperion_await_tx(self, tx_id):
        while True:
            resp = requests.get(
                f'{self.hyperion_api_endpoint}/v2/history/get_transaction',
                params={'id': tx_id}).json()

            if 'executed' not in resp:
                self.logger.warning(resp)

            if resp['executed']:
                break

            self.logger.info('await transaction:')
            self.logger.info(resp)
            time.sleep(0.1)

    def hyperion_get_actions(self, **kwargs):
        return requests.get(
            f'{self.hyperion_api_endpoint}/v2/history/get_actions',
            params=kwargs
        ).json()

    """ EVM RPC
    """

    def eth_gas_price(self) -> int:
        config = self.get_evm_config()
        assert len(config) == 1
        config = config[0]
        assert 'gas_price' in config
        return to_int(hexstr=f'0x{config["gas_price"]}')

    def eth_get_balance(self, addr: str) -> int:
        addr = remove_0x_prefix(addr)
        addr = ('0' * (12 * 2)) + addr
        rows = self.get_table(
            'eosio.evm', 'eosio.evm', 'account',
            '--key-type', 'sha256', '--index', '2',
            '--lower', addr,
            '--upper', addr)
        
        if len(rows) != 1:
            return None

        return int(rows[0]['balance'], 16)


    def eth_get_transaction_count(self, addr: str) -> int:
        addr = remove_0x_prefix(addr)
        addr = ('0' * (12 * 2)) + addr
        rows = self.get_table(
            'eosio.evm', 'eosio.evm', 'account',
            '--key-type', 'sha256', '--index', '2',
            '--lower', addr,
            '--upper', addr)
        
        if len(rows) != 1:
            return None

        return rows[0]['nonce']

    def eth_raw_tx(
        self,
        sender: str,
        data: str,
        gas_limit: str,
        value: str,
        to: str
    ):
        def encode(
            nonce: int,
            gas_price: str,
            gas_limit: str,
            to: str,
            value: str,
            data: str,
            v: int = 27,
            r: int = 0,
            s: int = 0
        ):
            l = [
                nonce,
                gas_price,
                gas_limit,
                to,
                value,
                data,
                v, r, s
            ]

            for i in range(len(l)):
                if l[i] is None:
                    raise ValueError(f'Parameter num {i} is None')

                if isinstance(l[i], str):
                    l[i] = decode_hex(l[i])

            return rlp.encode(l).hex()

        nonce = self.eth_get_transaction_count(sender)
        gas_price = self.eth_gas_price()

        return encode(
            nonce,
            gas_price,
            gas_limit,
            to,
            value,
            data
        )

    def eth_transfer(
        self,
        account: Name,
        sender: str,  # eth addr
        to: str,  # eth addr
        quantity: Asset,
        estimate_gas: bool = False
    ):
        raw_tx = self.eth_raw_tx(
            sender,
            0,
            DEFAULT_GAS_LIMIT,
            to_wei(quantity.amount, 'ether'),
            to
        )

        sender = remove_0x_prefix(sender)
        raw_tx = remove_0x_prefix(raw_tx)

        return self.push_action(
            EVM_CONTRACT,
            'raw',
            [account, raw_tx, estimate_gas, sender],
            f'{account}@active'
        )
        
