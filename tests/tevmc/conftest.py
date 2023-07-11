#!/usr/bin/env python3

import os
from shutil import copyfile
import sys

import pytest
import docker
import logging
import requests

from pathlib import Path
from contextlib import contextmanager

from tevmc import TEVMController
from tevmc.config import (
    local, testnet, mainnet,
    build_docker_manifest,
    randomize_conf_ports,
    randomize_conf_creds,
    add_virtual_networking
)
from tevmc.cmdline.init import touch_node_dir
from tevmc.cmdline.build import perform_docker_build, TEST_SERVICES
from tevmc.cmdline.cli import get_docker_client


@contextmanager
def bootstrap_test_stack(
    tmp_path_factory, config,
    randomize=True,
    services=TEST_SERVICES,
    from_latest=False,
    host_snapshot=None,
    **kwargs
):
    if randomize:
        config = randomize_conf_ports(config)
        config = randomize_conf_creds(config)

    if sys.platform == 'darwin':
        config = add_virtual_networking(config)

    client = get_docker_client()

    chain_name = config['telos-evm-rpc']['elastic_prefix']

    tmp_path = tmp_path_factory.getbasetemp() / chain_name
    build_docker_manifest(config)

    tmp_path.mkdir(parents=True, exist_ok=True)
    touch_node_dir(tmp_path, config, 'tevmc.json')
    perform_docker_build(
        tmp_path, config, logging, services)

    if host_snapshot:
        snapshot = Path(host_snapshot).name
        target_path = (tmp_path / 'docker' /
            config['nodeos']['docker_path'] /
            config['nodeos']['conf_dir'] / snapshot)
        copyfile(
            host_snapshot,
            target_path)

    containers = None

    try:
        with TEVMController(
            config,
            root_pwd=tmp_path,
            services=services,
            from_latest=from_latest,
            **kwargs
        ) as _tevmc:
            yield _tevmc
            containers = _tevmc.containers

    except BaseException:
        if containers:
            pid = os.getpid()

            client = get_docker_client(timeout=10)

            for val in containers:
                while True:
                    try:
                        container = client.containers.get(val)
                        container.stop()

                    except docker.errors.APIError as err:
                        if 'already in progress' in str(err):
                            time.sleep(0.1)
                            continue

                    except requests.exceptions.ReadTimeout:
                        print('timeout!')

                    except docker.errors.NotFound:
                        print(f'{val} not found!')

                    break
        raise


@pytest.fixture(scope='module')
def tevmc_local(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, local.default_config) as tevmc:
        yield tevmc


@pytest.fixture(scope='module')
def tevmc_local_non_rand(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, local.default_config, randomize=False) as tevmc:
        yield tevmc


@pytest.fixture(scope='module')
def tevmc_local_only_nodeos(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, local.default_config,
        services=['nodeos']
    ) as tevmc:
        yield tevmc


@pytest.fixture(scope='module')
def tevmc_testnet(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, testnet.default_config) as tevmc:
        yield tevmc

@pytest.fixture(scope='module')
def testnet_from_228038712(tmp_path_factory):
    import zstandard as zstd
    from urllib.request import urlretrieve

    snapshots_dir = Path('tests/tevmc/snapshots')
    snapshots_dir.mkdir(exist_ok=True, parents=True)

    snapshot_name = 'snapshot-2023-04-05-14-telostest-v6-0228038712.bin'
    host_snapshot = str(snapshots_dir / snapshot_name)

    # finally retrieve
    logging.info('Dowloading snapshot...')
    urlretrieve(
        'https://pub.store.eosnation.io/telostest-snapshots/snapshot-2023-04-05-14-telostest-v6-0228038712.bin.zst',
        host_snapshot + '.zst'
    )

    logging.info('done, decompress...')
    dctx = zstd.ZstdDecompressor()
    with open(host_snapshot + '.zst', 'rb') as ifh:
        with open(host_snapshot, 'wb') as ofh:
            dctx.copy_stream(ifh, ofh)

    config = dict(testnet.default_config)
    config['nodeos']['snapshot'] = f'/root/{snapshot_name}'
    config['nodeos']['ini']['plugins'].append('eosio::producer_api_plugin')

    config['telosevm-translator']['start_block'] = 228039000
    config['telosevm-translator']['deploy_block'] = 228039000
    config['telosevm-translator']['prev_hash'] = '30f184986cccf4725a8dc69c81030a7515d7f84ff18a0452c6cc6978488ce58e'

    logging.info('done, starting tevmc...')

    with bootstrap_test_stack(
        tmp_path_factory,
        config,
        wait=False,
        host_snapshot=host_snapshot,
        services=['elastic', 'nodeos', 'indexer']
    ) as tevmc:
        yield tevmc

@pytest.fixture(scope='module')
def tevmc_testnet_latest(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, testnet.default_config, from_latest=True) as tevmc:
        yield tevmc


@pytest.fixture(scope='module')
def tevmc_testnet_no_wait(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, testnet.default_config, wait=False) as tevmc:
        yield tevmc


@pytest.fixture(scope='module')
def tevmc_mainnet(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, mainnet.default_config) as tevmc:
        yield tevmc

@pytest.fixture(scope='module')
def tevmc_mainnet_latest(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, mainnet.default_config, from_latest=True) as tevmc:
        yield tevmc


@pytest.fixture(scope='module')
def tevmc_mainnet_no_wait(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, mainnet.default_config, wait=False) as tevmc:
        yield tevmc


@pytest.fixture(scope='module')
def tevmc_mainnet_translator_dev(tmp_path_factory):
    services = ['redis', 'elastic', 'nodeos']
    with bootstrap_test_stack(
        tmp_path_factory,
        mainnet.default_config,
        wait=False,
        randomize=False,
        services=services
    ) as tevmc:
        yield tevmc

from web3 import Account, Web3


@pytest.fixture(scope='module')
def local_w3(tevmc_local):
    tevmc = tevmc_local
    rpc_api_port = tevmc.config['telos-evm-rpc']['api_port']
    eth_api_endpoint = f'http://127.0.0.1:{rpc_api_port}/evm'

    w3 = Web3(Web3.HTTPProvider(eth_api_endpoint))
    assert w3.is_connected()

    yield w3


@pytest.fixture(scope='module')
def local_websocket_w3(tevmc_local):
    tevmc = tevmc_local
    rpc_ws_port = tevmc.config['telos-evm-rpc']['rpc_websocket_port']
    eth_ws_endpoint = f'ws://127.0.0.1:{rpc_ws_port}/evm'

    w3 = Web3(Web3.WebsocketProvider(eth_ws_endpoint))
    assert w3.is_connected()

    yield w3
