#!/usr/bin/env python3

import time
import json

from websocket import create_connection


def test_hyperion_websocket_local(tevmc_local):

    tevmc = tevmc_local

    rpc_ws_port = tevmc.config['hyperion']['chain']['telos-evm'][
        'rpcWebsocketPort']

    connected = False
    for i in range(3):
        try:
            ws = create_connection(
                f'ws://127.0.0.1:{rpc_ws_port}/evm')#, timeout=15)
            connected = True
            break

        except ConnectionRefusedError:
            time.sleep(5)

    assert connected

    # send subscribe packet
    ws.send(json.dumps({
        'id': 1,
        'method': 'eth_subscribe',
        'params': ['newHeads']
    }))

    msg = json.loads(ws.recv())
    tevmc.logger.info(msg)

    assert 'jsonrpc' in msg and msg['jsonrpc'] == '2.0'
    assert 'result' in msg
    assert 'id' in msg and msg['id'] == 1

    msg = json.loads(ws.recv())
    tevmc.logger.info(msg)

    assert 'difficulty' in msg
    assert 'extraData' in msg
    assert 'gasLimit' in msg
    assert 'miner' in msg
    assert 'nonce' in msg
    assert 'parentHash' in msg
    assert 'receiptsRoot' in msg
    assert 'sha3Uncles' in msg
    assert 'stateRoot' in msg
    assert 'transactionsRoot' in msg
    assert 'gasUsed' in msg
    assert 'logsBloom' in msg
    assert 'number' in msg
    assert 'timestamp' in msg


def test_hyperion_websocket_mainnet(tevmc_mainnet_no_wait):

    tevmc = tevmc_mainnet_no_wait

    rpc_ws_port = tevmc.config['hyperion']['chain']['telos-evm'][
        'rpcWebsocketPort']

    connected = False
    for i in range(3):
        try:
            ws = create_connection(
                f'ws://127.0.0.1:{rpc_ws_port}/evm')#, timeout=15)
            connected = True
            break

        except ConnectionRefusedError:
            time.sleep(5)

    assert connected

    # send subscribe packet
    ws.send(json.dumps({
        'id': 1,
        'method': 'eth_subscribe',
        'params': ['newHeads']
    }))

    msg = json.loads(ws.recv())
    tevmc.logger.info(msg)

    assert 'jsonrpc' in msg and msg['jsonrpc'] == '2.0'
    assert 'result' in msg
    assert 'id' in msg and msg['id'] == 1

    msg = json.loads(ws.recv())
    tevmc.logger.info(json.dumps(msg, indent=4))

    assert 'difficulty' in msg
    assert 'extraData' in msg
    assert 'gasLimit' in msg
    assert 'miner' in msg
    assert 'nonce' in msg
    assert 'parentHash' in msg
    assert 'receiptsRoot' in msg
    assert 'sha3Uncles' in msg
    assert 'stateRoot' in msg
    assert 'transactionsRoot' in msg
    assert 'gasUsed' in msg
    assert 'logsBloom' in msg
    assert 'number' in msg
    assert 'timestamp' in msg
