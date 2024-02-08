#!/usr/bin/env python3

from leap.sugar import random_string
from leap.tokens import tlos_token
from leap.protocol import Asset
from tevmc.testing import open_websocket_web3

from tevmc.utils import to_wei

from eth_account import Account


DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21000


def test_websocket_local_rpc(tevmc_local):
    '''Test the interaction of a local TEVMC blockchain instance through WebSocket RPC. 
    It covers creating native and EVM accounts, depositing tokens, transferring tokens 
    between EVM accounts, and verifying transactions via WebSocket.

    Args:
        tevmc_local: The local instance of the TEVMC blockchain client.
    '''

    # Initialize the local instance of the TEVMC blockchain client.
    tevmc = tevmc_local

    # Establish a WebSocket connection to the TEVMC using Web3.
    ws = open_websocket_web3(tevmc_local)

    # Create a new native blockchain account.
    account = tevmc.cleos.new_account()

    # Create a linked EVM account for the native account with a random name.
    ec, _ = tevmc.cleos.create_evm_account(account, random_string())
    assert ec == 0

    # Get the EVM (Ethereum-compatible) account address linked to the native account.
    primary = tevmc.cleos.eth_account_from_name(account)

    # Set an initial token amount for transfers.
    initial_tokens = Asset(102, tlos_token)

    # Transfer the initial token amount to the newly created native account.
    tevmc.cleos.transfer_token('eosio', account, initial_tokens, 'evm test')

    # Deposit the tokens to the linked EVM account from the native account.
    tevmc.cleos.transfer_token(account, 'eosio.evm', initial_tokens, 'Deposit')

    # Create an actual EVM (Ethereum-compatible) account.
    address = Account.create()

    # Transfer tokens from the primary EVM account to the new EVM account.
    ec, out = tevmc.cleos.eth_transfer(
        account,
        primary,
        address.address,
        Asset(initial_tokens.amount - 1, tlos_token)
    )
    assert ec == 0

    # Create a secondary EVM account.
    secondary = Account.create()

    # Calculate the amount of tokens to transfer from the first EVM account to the secondary one.
    quantity = ws.eth.get_balance(address.address) - to_wei(1, 'ether')

    # Construct and sign a raw transaction for the token transfer.
    tx_hash = ws.eth.send_raw_transaction(
        Account.sign_transaction({
            'from': address.address,
            'to': secondary.address,
            'gas': DEFAULT_GAS,
            'gasPrice': DEFAULT_GAS_PRICE,
            'value': quantity,
            'data': b'',
            'nonce': 0,
            'chainId': tevmc.cleos.chain_id
        }, address.key).rawTransaction
    )

    # Wait for the transaction to be processed and obtain its receipt.
    receipt = ws.eth.wait_for_transaction_receipt(tx_hash)

    # Ensure the transaction was successful.
    assert receipt['status'] == 1

