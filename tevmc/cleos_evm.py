#!/usr/bin/env python3

import json

from base64 import b64encode
from pathlib import Path

import rlp
import requests

from rlp.sedes import (
    big_endian_int,
    binary,
    Binary
)

from leap.cleos import CLEOS
from leap.protocol import Asset

from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount

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
        evm_url: str = 'http://localhost:7000/evm',
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.evm_url = evm_url
        self.chain_id = chain_id

        self._w3 = Web3(Web3.HTTPProvider(evm_url))

        self.evm_contracts = {}

        self.evm_default_account: LocalAccount = Account.from_key(
            '0x87ef69a835f8cd0c44ab99b7609a20b2ca7f1c8470af4f0e5b44db927d542084')

    def deploy_evm(
        self,
        contract_path,
        start_bytes: int = 2684354560,
        start_cost: str = '21000.0000 TLOS',
        target_free: int = 2684354560,
        min_buy: int = 20000,
        fee_transfer_pct: int = 100,
        gas_per_byte: int = 69
    ):
        master_key = self.keys['eosio']

        # create evm accounts
        self.new_account(
            'eosio.evm',
            key=master_key,
            ram=start_bytes)

        self.new_account(
            'fees.evm',
            key=master_key,
            ram=100000)

        # ram_price_post = self.get_ram_price()

        # start_cost = Asset(ram_price_post.amount * start_bytes, sys_token)

        self.new_account(
            'rpc.evm',
            key=master_key,
            cpu='10000.0000 TLOS',
            net='10000.0000 TLOS',
            ram=100000)

        self.create_snapshot({})

        self.logger.info('deploying evm contract')

        self.evm_deploy_info = self.deploy_contract_from_path(
            'eosio.evm',
            contract_path,
            privileged=True,
            create_account=False
        )

        self.evm_init_info = self.push_action(
            'eosio.evm',
            'init',
            [
                start_bytes,
                start_cost,
                target_free,
                min_buy,
                fee_transfer_pct,
                gas_per_byte
            ],
            'eosio.evm'
        )

        self.push_action(
            'eosio.evm', 'setrevision', [1], 'eosio.evm')

    def create_test_evm_account(
        self,
        name: str = 'evmuser1',
        data: str = 'foobar',
        truffle_addr: str = '0xf79b834a37f3143f4a73fc3934edac67fd3a01cd'
    ):
        self.new_account(
            name,
            key=self.keys['eosio'])

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

        gas_allowance = 20

        total_needed = sum([q for a, q in addr_amount_pairs]) + gas_allowance

        self.create_evm_account(name, data)
        quantity = Asset.from_ints(total_needed * (10 ** 4), 4, 'TLOS')

        self.transfer_token('eosio', name, quantity, ' ')
        self.transfer_token(name, 'eosio.evm', quantity, 'Deposit')

        self.wait_blocks(3)

        eth_addr = self.eth_account_from_name(name)
        assert eth_addr

        self.logger.info(f'{name}: {eth_addr}')

        for addr, amount in addr_amount_pairs:
            self.eth_transfer(
                eth_addr,
                addr,
                Asset.from_ints(amount * (10 ** 4), 4, 'TLOS'),
                account='evmuser1'
            )


    """    eosio.evm interaction
    """

    def get_evm_config(self):
        return self.get_table(
            'eosio.evm', 'eosio.evm', 'config')

    def get_evm_resources(self):
        return self.get_table(
            'eosio.evm', 'eosio.evm', 'resources')

    def eth_account_from_name(self, name) -> str | None:
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
            account,
            key=self.get_private_key(account)
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

    def eth_get_transaction_receipt(self, transaction_hash, url=None):
        payload = {
            'jsonrpc': '2.0',
            'method': 'eth_getTransactionReceipt',
            'params': [transaction_hash],
            'id': 1
        }
        response = requests.post(
            url if url else self.evm_url,
            json=payload,
            headers={'Content-Type': 'application/json'})
        return response.json() if response.status_code == 200 else None

    def eth_get_code(self, address, block='latest', url=None):
        payload = {
            'jsonrpc': '2.0',
            'method': 'eth_getCode',
            'params': [address, block],
            'id': 1
        }
        response = requests.post(
            url if url else self.evm_url,
            json=payload,
            headers={'Content-Type': 'application/json'})
        return response.json() if response.status_code == 200 else None

    def eth_raw_tx(
        self,
        sender: str,
        data: str | bytes,
        gas: str,
        value: int,
        to: str | bytes
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

        return tx.encode()

    def eth_transfer(
        self,
        sender: str,  # eth addr
        to: str,  # eth addr
        quantity: Asset | str,
        account: str = 'eosio',
        estimate_gas: bool = False
    ):
        quantity = Asset.from_str(quantity)

        amount = quantity.amount // (10 ** quantity.symbol.precision)

        raw_tx = self.eth_raw_tx(
            sender,
            '',
            DEFAULT_GAS_LIMIT,
            to_wei(amount, 'ether'),
            to
        )

        self.logger.info('doing eth transfer...')
        self.logger.info(json.dumps({
            'account': account,
            'sender': sender,
            'to': to,
            'quantity': amount,
            'wei': to_wei(amount, 'ether')
        }, indent=4))

        sender = remove_0x_prefix(sender)

        return self.push_action(
            EVM_CONTRACT,
            'raw',
            [
                account,
                raw_tx,
                estimate_gas,
                sender
            ],
            account,
            key=self.get_private_key(account)
        )

    def eth_withdraw(self,
        quantity: str,
        to: str,
        account: str | None = None,
    ):
        if not account:
            account = to

        return self.push_action(
            EVM_CONTRACT,
            'withdraw',
            [to, quantity],
            account,
            key=self.get_private_key(account)
        )

    def eth_get_block_by_number(
        self,
        block_number: int | str,
        full_transactions: bool= False,
        url: str | None = None
    ):
        headers = {'Content-Type': 'application/json'}
        payload = {
            'jsonrpc': '2.0',
            'method': 'eth_getBlockByNumber',
            'params': [
                block_number,
                full_transactions
            ],
            'id': 1
        }
        response = requests.post(
            url if url else self.evm_url,
            json=payload, headers=headers)
        return response.json() if response.status_code == 200 else None

    def eth_deploy_contract_from_json(
        self,
        contract_path: str | Path,
        contract_name: str,
        constructor_arguments: list[str] = [],
        account: LocalAccount | None = None,
        max_gas: int = int(1e8)
    ):
        if not isinstance(account, LocalAccount):
            account = self.evm_default_account

        with open(contract_path, 'r') as contract_fp:
            contract_interface = json.load(contract_fp)

        # instantiate
        Contract = self._w3.eth.contract(
            abi=contract_interface['abi'],
            bytecode=contract_interface['bytecode']
        )

        # create deploy tx
        tx_args = {
            'from': account.address,
            'gas': max_gas,
            'gasPrice': self._w3.eth.gas_price,
            'nonce': self._w3.eth.get_transaction_count(account=account.address)
        }

        tx = Contract.constructor(*constructor_arguments).build_transaction(tx_args)

        signed_tx = account.sign_transaction(tx)

        tx_hash = self._w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        tx_receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash)

        _contract = self._w3.eth.contract(
            address=tx_receipt['contractAddress'], abi=contract_interface['abi'])

        self.evm_contracts[contract_name] = _contract

        return _contract

    # substitution helpers

    def subst_status(self, account: str | None = None) -> dict:
        params = {}
        if isinstance(account, str):
            params['account'] = account

        return self._post(
            '/v1/subst/status', params=params)

    def subst_upsert(self, account: str, from_block: int, code: bytes, must_activate: bool = True) -> dict:
        return self._post(
            '/v1/subst/upsert',
            params={
                'account': account,
                'from_block': from_block,
                'code': b64encode(code).decode('utf-8'),
                'must_activate': must_activate
            }
        )

    def subst_activate(self, account: str | None = None) -> dict:
        params = {}
        if isinstance(account, str):
            params['account'] = account

        return self._post('/v1/subst/activate', params=params)

    def subst_deactivate(self, account: str | None = None) -> dict:
        params = {}
        if isinstance(account, str):
            params['account'] = account

        return self._post('/v1/subst/deactivate', params=params)

    def subst_remove(self, account: str | None = None) -> dict:
        params = {}
        if isinstance(account, str):
            params['account'] = account

        return self._post('/v1/subst/remove', params=params)

    def subst_fetch_manifest(self) -> dict:
        return self._get('/v1/subst/fetch_manifest')

