#!/usr/bin/env python3

import time
import json
import requests

from typing import Optional, Union, Dict

import rlp

from rlp.sedes import (
    big_endian_int,
    binary,
    Binary
)

from leap.cleos import CLEOS
from leap.sugar import Name, Asset

from .utils import to_wei, to_int, decode_hex, remove_0x_prefix


EVM_CONTRACT = 'eosio.evm'
DEFAULT_GAS_PRICE = '0x01'
DEFAULT_GAS_LIMIT = '0x1e8480'
DEFAULT_VALUE = '0x00'
DEFAULT_DATA = '0x00'


address = Binary.fixed_length(20, allow_empty=True)


class EVMTransaction(rlp.Serializable):
    fields = [
        ('nonce', big_endian_int),
        ('gas_price', big_endian_int),
        ('gas', big_endian_int),
        ('to', address),
        ('value', big_endian_int),
        ('data', binary)
        # ('v', big_endian_int),
        # ('r', big_endian_int),
        # ('s', big_endian_int)
    ]

    def encode(self) -> bytes:
        return rlp.encode(self)


class CLEOSEVM(CLEOS):

    def __init__(
        self,
        *args,
        chain_id: int = 41,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.chain_id = chain_id

        self.__jsonrpc_id = 0

    def deploy_evm(
        self,
        start_bytes: int = 2684354560,
        start_cost: str = '21000.0000 TLOS',
        target_free: int = 2684354560,
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

        # ram_price_post = self.get_ram_price()

        # start_cost = Asset(ram_price_post.amount * start_bytes, sys_token)

        self.new_account(
            'rpc.evm',
            key='EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L',
            cpu=10000.0000,
            net=10000.0000,
            ram=100000)

        contract_path = '/opt/eosio/bin/contracts/eosio.evm/receiptless'

        self.evm_deploy_info = self.deploy_contract(
            'eosio.evm', contract_path,
            privileged=True,
            create_account=False,
            verify_hash=False)

        ec, self.evm_init_info = self.push_action(
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
        quantity = Asset(111000000, self.sys_token_supply.symbol)

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
                Asset(amount, self.sys_token_supply.symbol)
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
            index_position=3,
            key_type='name',
            lower_bound=name,
            upper_bound=name
        )

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

    """ EVM
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
            index_position=2,
            key_type='sha256',
            lower_bound=addr,
            upper_bound=addr
        )

        if len(rows) != 1:
            return None

        return int(rows[0]['balance'], 16)


    def eth_get_transaction_count(self, addr: str) -> int:
        addr = remove_0x_prefix(addr)
        addr = ('0' * (12 * 2)) + addr
        rows = self.get_table(
            'eosio.evm', 'eosio.evm', 'account',
            index_position=2,
            key_type='sha256',
            lower_bound=addr,
            upper_bound=addr
        )

        if len(rows) != 1:
            return None

        return rows[0]['nonce']

    def eth_raw_tx(
        self,
        sender: str,
        data: Union[str, bytes],
        gas: str,
        value: int,
        to: Union[str, bytes]
    ):
        if isinstance(gas, str):
            gas = to_int(hexstr=gas)

        nonce = self.eth_get_transaction_count(sender)
        gas_price = self.eth_gas_price()

        if isinstance(data, str):
            data = decode_hex(data)

        if isinstance(to, str):
            to = decode_hex(to)

        tx = EVMTransaction(
            nonce=nonce,
            gas_price=gas_price,
            gas=gas,
            to=to,
            value=value,
            data=data
        )

        return tx.encode().hex()

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
            '',
            DEFAULT_GAS_LIMIT,
            to_wei(quantity.amount, 'ether'),
            to
        )

        sender = remove_0x_prefix(sender)
        raw_tx = remove_0x_prefix(raw_tx)

        self.logger.info('doing eth transfer...')
        self.logger.info(json.dumps({
            'account': account,
            'sender': sender,
            'to': to,
            'quantity': quantity.amount,
            'wei': to_wei(quantity.amount, 'ether')
        }, indent=4))

        return self.push_action(
            EVM_CONTRACT,
            'raw',
            [account, raw_tx, estimate_gas, sender],
            f'{account}@active'
        )

    def eth_withdraw(self,
        account: Name,
        quantity: Asset,
        to: Name
    ):
        return self.push_action(
            EVM_CONTRACT,
            'withdraw',
            [to, quantity],
            f'{account}@active'
        )
