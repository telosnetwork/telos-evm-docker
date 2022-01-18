#!/usr/bin/env python3

import time
import requests

from typing import Optional

import rlp

from web3 import Web3
from py_eosio.cleos import CLEOS
from py_eosio.sugar import Name, Asset
from eth_utils import to_wei, to_int, decode_hex, remove_0x_prefix


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

        return Web3.toChecksumAddress(f'0x{rows[0]["address"]}')

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

    def hyperion_health(self) -> int:
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

    def init_w3(self):
        self.w3 = Web3(
            Web3.HTTPProvider(self.hyperion_api_endpoint + '/evm'))

    def eth_gas_price(self) -> int:
        config = self.get_evm_config()
        assert len(config) == 1
        config = config[0]
        assert 'gas_price' in config
        return to_int(hexstr=f'0x{config["gas_price"]}')

    # def eth_get_transaction_count(self, addr: str) -> int:
    #     resp = requests.get(
    #         f'{self.hyperion_api_endpoint}/v2/evm/get_transactions',
    #         params={'address': addr}
    #     ).json()
    #     return resp['total']['value'] 

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
            v: int = 0,
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

        nonce = self.w3.eth.get_transaction_count(sender)
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
        
