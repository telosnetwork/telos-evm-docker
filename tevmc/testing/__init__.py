#!/usr/bin/env python3

import sys
import time
import docker
import logging
import tarfile
import requests

from shutil import copyfile
from pathlib import Path
from contextlib import contextmanager

import pytest

from web3 import Web3

from tevmc import TEVMController
from tevmc.config import (
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


def maybe_get_marker(request, mark_name: str, field: str, default):
    mark = request.node.get_closest_marker(mark_name)
    if mark is None:
        return default
    else:
        return getattr(mark, field)


def get_marker(request, mark_name: str, field: str):
    mark = maybe_get_marker(request, mark_name, field, None)
    if mark is None:
        raise ValueError(
            f'{mark_name} mark required, did you forgot to mark the test?')
    else:
        return mark


@contextmanager
def bootstrap_test_stack(request, tmp_path_factory):
    config = get_marker(request, 'config', 'kwargs')
    tevmc_params = maybe_get_marker(
        request, 'tevmc_params', 'kwargs', {})

    custom_subst_abi = maybe_get_marker(
        request, 'custom_subst_abi', 'args', [None])[0]
    custom_subst_wasm = maybe_get_marker(
        request, 'custom_subst_wasm', 'args', [None])[0]
    custom_nodeos_tar = maybe_get_marker(
        request, 'custom_nodeos_tar', 'args', [None])[0]

    randomize = maybe_get_marker(request, 'randomize', 'args', [True])[0]

    services = maybe_get_marker(
        request, 'services', 'args', TEST_SERVICES)

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

    if custom_subst_wasm:
        copyfile(
            custom_subst_wasm,
            tmp_path / 'docker/leap/contracts/eosio.evm/regular/regular.wasm'
        )

    if custom_subst_abi:
        copyfile(
            custom_subst_abi,
            tmp_path / 'docker/leap/contracts/eosio.evm/regular/regular.abi'
        )

    if custom_nodeos_tar:
        tar_path = Path(custom_nodeos_tar)
        extensionless_path = Path(tar_path.stem).stem

        bin_name = str(extensionless_path)

        host_config_path = tmp_path / 'docker/leap/config'

        with tarfile.open(custom_nodeos_tar, 'r:gz') as file:
            file.extractall(path=host_config_path)

        binary = f'{bin_name}/usr/local/bin/nodeos'

        assert (host_config_path / binary).is_file()

        config['nodeos']['nodeos_bin'] = '/root/' + binary

    perform_docker_build(
        tmp_path, config, logging, services)

    containers = None

    try:
        with TEVMController(
            config,
            root_pwd=tmp_path,
            services=services,
            **tevmc_params
        ) as _tevmc:
            yield _tevmc
            containers = _tevmc.containers

    except BaseException:
        if containers:
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
def tevm_node(request, tmp_path_factory):
    with bootstrap_test_stack(request, tmp_path_factory) as tevmc:
        yield tevmc


def open_web3(tevm_node):
    rpc_api_port = tevm_node.config['telos-evm-rpc']['api_port']
    eth_api_endpoint = f'http://127.0.0.1:{rpc_api_port}/evm'

    w3 = Web3(Web3.HTTPProvider(eth_api_endpoint))
    assert w3.is_connected()

    return w3


def open_websocket_web3(tevm_node):
    rpc_ws_port = tevm_node.config['telos-evm-rpc']['rpc_websocket_port']
    eth_ws_endpoint = f'ws://127.0.0.1:{rpc_ws_port}/evm'

    w3 = Web3(Web3.WebsocketProvider(eth_ws_endpoint))
    assert w3.is_connected()

    return w3
