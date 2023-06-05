#!/usr/bin/env python3

import os
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
from tevmc.cmdline.build import perform_docker_build
from tevmc.cmdline.clean import clean
from tevmc.cmdline.cli import get_docker_client


TEST_SERVICES = ['redis', 'elastic', 'kibana', 'nodeos', 'indexer', 'rpc']


@contextmanager
def bootstrap_test_stack(
    tmp_path_factory, config,
    randomize=True,
    services=TEST_SERVICES,
    from_latest=False,
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
    manifest = build_docker_manifest(config)

    tmp_path.mkdir(parents=True, exist_ok=True)
    touch_node_dir(tmp_path, config, 'tevmc.json')
    perform_docker_build(
        tmp_path, config, logging)

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
