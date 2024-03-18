#!/usr/bin/env python3

import json
import pytest
import subprocess

from tevmc.testing import open_web3


def batch_request(payload: list, rpc_endpoint):
    json_payload = json.dumps(payload)

    curl_command = [
        "curl", "-X", "POST",
        "-H", "Content-Type: application/json",
        "--data", json_payload,
        rpc_endpoint
    ]

    result = subprocess.run(curl_command, capture_output=True, text=True)

    if result.returncode == 0:
        response_data = json.loads(result.stdout)
        return response_data
    else:
        return []


def block_batch_request(start_block, num_blocks, rpc_endpoint):
    payload = [
        {"jsonrpc": "2.0", "method": "eth_getBlockByNumber", "params": [start_block + i, True], "id": i + 1}
        for i in range(num_blocks)
    ]
    return batch_request(payload, rpc_endpoint)



def compare_w3_block_w_batch_block(batch_block, w3_block):
    assert int(batch_block['difficulty'], 16) == w3_block['difficulty']
    assert batch_block['extraData'] == w3_block['extraData'].hex()
    assert int(batch_block['gasLimit'], 16) == w3_block['gasLimit']
    assert int(batch_block['gasUsed'], 16) == w3_block['gasUsed']
    assert batch_block['hash'] == w3_block['hash'].hex()
    assert batch_block['logsBloom'] == w3_block['logsBloom'].hex()
    assert batch_block['miner'] == w3_block['miner']
    assert batch_block['nonce'] == w3_block['nonce'].hex()
    assert int(batch_block['number'], 16) == w3_block['number']
    assert batch_block['parentHash'] == w3_block['parentHash'].hex()
    assert batch_block['receiptsRoot'] == w3_block['receiptsRoot'].hex()
    assert batch_block['sha3Uncles'] == w3_block['sha3Uncles'].hex()
    assert int(batch_block['size'], 16) == w3_block['size']
    assert batch_block['stateRoot'] == w3_block['stateRoot'].hex()
    assert int(batch_block['timestamp'], 16) == w3_block['timestamp']
    assert int(batch_block['totalDifficulty'], 16) == w3_block['totalDifficulty']
    assert len(batch_block['transactions']) == len(w3_block['transactions'])
    assert batch_block['transactionsRoot'] == w3_block['transactionsRoot'].hex()
    assert len(batch_block['uncles']) == len(w3_block['uncles'])


@pytest.mark.tevmc_params(wait=False)
def test_rpc_batch_vs_single(tevmc_mainnet):
    tevmc = tevmc_mainnet
    w3 = open_web3(tevmc)

    start_block = tevmc.config['telosevm-translator']['start_block']

    batch_size = 1000
    batch = block_batch_request(start_block, batch_size, tevmc.cleos.evm_url)


    for i, block in enumerate(batch):
        compare_w3_block_w_batch_block(
            block, w3.eth.get_block(start_block + i))


@pytest.mark.tevmc_params(wait=False)
def test_rpc_batch_multi_type(tevmc_mainnet):
    tevmc = tevmc_mainnet
    w3 = open_web3(tevmc)

    start_block = tevmc.config['telosevm-translator']['start_block']
    num_calls = 1000
    payload = []

    for i in range(num_calls):
        if i % 2 == 0:
            payload.append({
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": [start_block + i, True],
                "id": i + 1
            })

        else:
            payload.append({
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": i + 1
            })

    batch = batch_request(payload, tevmc.cleos.evm_url)

    for i, block in enumerate(batch):
        if i % 2 == 0:
            compare_w3_block_w_batch_block(
                block, w3.eth.get_block(start_block + i))


def test_rpc_across_index(tevmc_local):
    tevmc = tevmc_local
    w3 = open_web3(tevmc)

    start_block = 800
    batch_size = 400
    tevmc.cleos.wait_block(start_block + batch_size)

    batch = block_batch_request(start_block, batch_size, tevmc.cleos.evm_url)

    for i, block in enumerate(batch):
        compare_w3_block_w_batch_block(
            block, w3.eth.get_block(start_block + i))
