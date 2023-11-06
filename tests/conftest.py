#!/usr/bin/env python3

import logging
import time
from typing import Dict, List
import pdbp
import subprocess

from datetime import timedelta

import pytest
import requests

from leap.sugar import get_free_port

from tevmc.config import local, testnet, mainnet
from tevmc.testing import bootstrap_test_stack, get_marker, maybe_get_marker
from tevmc.testing.database import get_suffix

from elasticsearch import Elasticsearch


@pytest.fixture()
def tevmc_local(request, tmp_path_factory):
    request.applymarker(pytest.mark.config(**local.default_config))
    with bootstrap_test_stack(request, tmp_path_factory) as tevmc:
        yield tevmc


@pytest.fixture()
def tevmc_testnet(request, tmp_path_factory):
    request.applymarker(pytest.mark.config(**testnet.default_config))
    with bootstrap_test_stack(request, tmp_path_factory) as tevmc:
        yield tevmc


@pytest.fixture()
def tevmc_mainnet(request, tmp_path_factory):
    request.applymarker(pytest.mark.config(**mainnet.default_config))
    with bootstrap_test_stack(request, tmp_path_factory) as tevmc:
        yield tevmc


def prepare_db_for_test(
    tevmc,
    start_time,
    ranges,
    txs=[],
    action_index_spec='action-v1.5',
    delta_index_spec='delta-v1.5',
    docs_per_index=10_000_000
):
    rpc_conf = tevmc.config['telos-evm-rpc']
    es_config = tevmc.config['elasticsearch']
    es = Elasticsearch(
        f'{es_config["protocol"]}://{es_config["host"]}',
        basic_auth=(
            es_config['user'], es_config['pass']
        )
    )
    es.indices.delete(
        index=f'{rpc_conf["elastic_prefix"]}-{action_index_spec}-*'
    )
    es.indices.delete(
        index=f'{rpc_conf["elastic_prefix"]}-{delta_index_spec}-*',
    )

    ops = []
    for rstart, rend in ranges:
        for i in range(rstart, rend + 1, 1):
            delta_index = f'{rpc_conf["elastic_prefix"]}-{delta_index_spec}-{get_suffix(i, docs_per_index)}'
            ops.append({
                "index": {
                    "_index": delta_index
                }
            })
            ops.append({
                "@timestamp": start_time + (i * timedelta(seconds=0.5)),
                "@global": {
                    "block_num": i
                },
                "block_num": i - 10
            })

    indices = []
    for tx in txs:
        action_index = f'{rpc_conf["elastic_prefix"]}-{action_index_spec}-{get_suffix(tx["@raw.block"], docs_per_index)}'
        indices.append(action_index)
        ops.append({
            "index": {
                "_index": action_index
            }
        })
        ops.append(tx)

    for idx in indices:
        es.indices.create(
            index=idx,
            ignore=400,
            body={
                'mappings': {
                    'properties': {
                        '@raw.hash': {
                            'type': 'keyword'
                        }
                    }
                }
            }
        )


    es.bulk(operations=ops, refresh=True)



class ShipMocker:

    def __init__(
        self,
        control_endpoint: str,
        ship_endpoint: str
    ):
        self.control_endpoint = control_endpoint
        self.ship_endpoint = ship_endpoint

    def set_block(self, num: int):
        return requests.post(
            f'{self.control_endpoint}/set_block',
            json={'num': num}
        )

    def set_jumps(self, jumps: Dict[int, int], index: int = 0):
        return requests.post(
            f'{self.control_endpoint}/set_jumps',
            json={'jumps': jumps, 'index': index}
        )

    def set_block_info(self, blocks: List[str], index: int):
        return requests.post(
            f'{self.control_endpoint}/set_block_info',
            json={'blocks': blocks, 'index': index}
        )


@pytest.fixture
def ship_mocker(request):
    start_block = get_marker(
        request, 'start_block', 'args')[0]
    end_block = get_marker(
        request, 'end_block', 'args')[0]

    chain_id = maybe_get_marker(
        request, 'chain_id', 'args', [None])[0]
    start_time = maybe_get_marker(
        request, 'start_time', 'args', [None])[0]

    jumps = maybe_get_marker(
        request, 'jumps', 'args', [()])[0]

    blocks = maybe_get_marker(
        request, 'blocks', 'args', [()])[0]

    cmd = [
        'node', 'shipMocker.js', 'run',
        str(start_block), str(end_block)
    ]

    # ship_port = get_free_port()
    # control_port = get_free_port()

    # cmd += ['--shipPort', str(ship_port)]
    # cmd += ['--controlPort', str(control_port)]

    if chain_id:
        cmd += ['--chainId', chain_id]

    if start_time:
        cmd += ['--startTime', start_time]

    proc = subprocess.Popen(
        cmd, cwd='tests/ship-mock/build',
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    time.sleep(1)

    exit_code = proc.poll()
    if exit_code:
        stdout, stderr = proc.communicate()
        stdout = stdout.decode()
        stderr = stderr.decode()
        raise subprocess.SubprocessError(
            f'Couldn\'t start ship mocker:\nstdout:\n{stdout}\nstderr:\n{stderr}')

    client = ShipMocker(
        f'http://127.0.0.1:6970', f'http://127.0.0.1:29999')

    if len(blocks) > 0:
        for i, block_sequence in enumerate(blocks):
            client.set_block_info(block_sequence, i)

    if len(jumps) > 0:
        client.set_jumps(jumps)

    yield client

    proc.terminate()
    stdout, stderr = proc.communicate()
    stdout = stdout.decode()
    stderr = stderr.decode()
    logging.info(stdout)
    logging.info(stderr)
