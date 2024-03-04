#!/usr/bin/env python3

import pdbp
import logging
import subprocess

from copy import deepcopy
from pathlib import Path
from datetime import timedelta

import pytest

from tevmc.config import local, testnet, mainnet
from tevmc.testing import bootstrap_test_stack
from tevmc.testing.database import get_suffix

from elasticsearch import Elasticsearch


@pytest.fixture()
def tevmc_local(request, tmp_path_factory):
    request.applymarker(pytest.mark.config(**local.default_config))
    with bootstrap_test_stack(request, tmp_path_factory) as tevmc:
        yield tevmc


@pytest.fixture()
def subst_testing_nodeos(request, tmp_path_factory):
    config = deepcopy(local.default_config)

    config['nodeos']['ini']['subst'] = {}

    request.applymarker(pytest.mark.config(**config))
    request.applymarker(pytest.mark.services('nodeos'))
    request.applymarker(pytest.mark.randomize(False))
    request.applymarker(pytest.mark.tevmc_params(testing=True, skip_init=True))
    with bootstrap_test_stack(request, tmp_path_factory) as tevmc:
        yield tevmc


@pytest.fixture()
def subst_testing_nodeos_testcontract(request, tmp_path_factory):
    config = deepcopy(local.default_config)

    config['nodeos']['ini']['subst'] = {
        'testcontract': '/opt/eosio/bin/testcontracts/testcontract/variations/testcontract.var1.wasm'
    }

    request.applymarker(pytest.mark.config(**config))
    request.applymarker(pytest.mark.services('nodeos'))
    request.applymarker(pytest.mark.randomize(False))
    request.applymarker(pytest.mark.tevmc_params(testing=True, skip_init=True))
    with bootstrap_test_stack(request, tmp_path_factory) as tevmc:

        tevmc.cleos.deploy_contract_from_path(
            'testcontract',
            Path('tests/contracts/testcontract/base'),
            contract_name='testcontract'
        )

        yield tevmc


@pytest.fixture()
def compile_evm():
    # maybe compile uniswap v2 core
    uswap_v2_dir = Path('tests/evm-contracts/uniswap-v2-core')
    if not (uswap_v2_dir / 'build').exists():

        # run yarn & compile separate cause their script dies
        # installing optional deps and this is ok
        process = subprocess.run(
            'yarn',
            shell=True, cwd=uswap_v2_dir,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        if process.returncode != 0:
            last_line = process.stdout.splitlines()[-1]
            if 'you can safely ignore this error' not in last_line:
                logging.error(process.stdout)
                raise ChildProcessError(f'Failed to install uniswap v2 core deps')

        process = subprocess.run(
            'yarn compile',
            shell=True, cwd=uswap_v2_dir,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        if process.returncode != 0:
            logging.error(process.stdout)
            raise ChildProcessError(f'Failed to compile uniswap v2 core')


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

