#!/usr/bin/env python3

import json

from websocket import create_connection


def test_loop(tevmc_local):
    breakpoint()

def test_hyperion_websocket(tevmc_local):

    tevmc = tevmc_local

    rpc_ws_port = tevmc.config['hyperion']['chain']['telos-evm'][
        'rpcWebsocketPort']

    ws = create_connection(f'ws://localhost:{rpc_ws_port}/evm', timeout=5)


    # indexer_ws_uri = tevmc.config['hyperion']['chain']['telos-evm'][
    #     'indexerWebsocketUri']

    # ws = create_connection(indexer_ws_uri, timeout=5)

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
    assert True
