#!/usr/bin/env python3

import json


def test_websocket_local_new_heads(tevmc_local):
    '''Test the WebSocket RPC interaction with a local TEVMC instance to subscribe to 'newHeads' 
    events. Verifies that the received message adheres to the expected Ethereum JSON-RPC 
    format and contains the necessary data fields for a new block header.

    Args:
        tevmc_local: The local instance of the TEVMC blockchain client.
    '''

    # Initializing the local TEVMC instance.
    tevmc = tevmc_local

    # Opening a WebSocket connection to the local RPC.
    ws = tevmc.open_rpc_websocket()

    # Sending a subscription request to listen to new block headers ('newHeads').
    ws.send(json.dumps({
        'id': 1,
        'method': 'eth_subscribe',
        'params': ['newHeads']
    }))

    # Receiving the subscription confirmation message.
    msg = json.loads(ws.recv())
    tevmc.logger.info(json.dumps(msg, indent=4))

    # Verifying the structure and values of the subscription confirmation message.
    assert 'jsonrpc' in msg and msg['jsonrpc'] == '2.0'
    assert 'result' in msg
    assert 'id' in msg and msg['id'] == 1

    # Storing the subscription ID for later comparison.
    sub_id = msg['result']

    # Receiving the actual 'newHeads' message with the block header details.
    msg = json.loads(ws.recv())
    tevmc.logger.info(json.dumps(msg, indent=4))

    # Verifying the structure and values of the received 'newHeads' message.
    assert 'jsonrpc' in msg and msg['jsonrpc'] == '2.0'
    assert 'method' in msg and msg['method'] == 'eth_subscription'
    assert 'params' in msg

    # Extracting the parameters which contain the block header details.
    params = msg['params']

    # Ensuring the received message corresponds to our earlier subscription.
    assert 'subscription' in params and params['subscription'] == sub_id
    assert 'result' in params

    # Extracting the actual block header details.
    result = params['result']

    # Verifying the block header contains all expected fields.
    assert 'difficulty' in result
    assert 'extraData' in result
    assert 'gasLimit' in result
    assert 'miner' in result
    assert 'nonce' in result
    assert 'hash' in result
    assert 'parentHash' in result
    assert 'receiptsRoot' in result
    assert 'sha3Uncles' in result
    assert 'stateRoot' in result
    assert 'transactionsRoot' in result
    assert 'gasUsed' in result
    assert 'logsBloom' in result
    assert 'number' in result
    assert 'timestamp' in result

