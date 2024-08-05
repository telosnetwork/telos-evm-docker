#!/usr/bin/env python3

import sys
import time
import json
import docker
import tarfile
import requests

import pytest

from shutil import copyfile
from pathlib import Path
from contextlib import contextmanager

from web3 import Web3
from leap.sugar import download_snapshot

from tevmc.config import (
    randomize_conf_ports,
    randomize_conf_creds,
    add_virtual_networking
)
from tevmc.cmdline.init import touch_node_dir
from tevmc.cmdline.cli import get_docker_client


TEST_SERVICES = ['redis', 'elastic', 'nodeos', 'indexer', 'rpc']


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
    from tevmc import TEVMController

    config = get_marker(request, 'config', 'kwargs')
    chain_name = config['telos-evm-rpc']['elastic_prefix']
    tevmc_params = maybe_get_marker(
        request, 'tevmc_params', 'kwargs', {})

    custom_subst_wasm = maybe_get_marker(
        request, 'custom_subst_wasm', 'args', [None])[0]
    custom_nodeos_tar = maybe_get_marker(
        request, 'custom_nodeos_tar', 'args', [None])[0]
    from_snap = maybe_get_marker(
        request, 'from_snapshot', 'args', [None])[0]
    from_snap_file = maybe_get_marker(
        request, 'from_snapshot_file', 'kwargs', None)
    node_dir = Path(maybe_get_marker(
        request, 'node_dir', 'args', [tmp_path_factory.getbasetemp() / chain_name])[0])

    randomize = maybe_get_marker(request, 'randomize', 'args', [True])[0]

    services = list(maybe_get_marker(
        request, 'services', 'args', TEST_SERVICES))

    if randomize:
        config = randomize_conf_ports(config)
        config = randomize_conf_creds(config)

    if sys.platform == 'darwin':
        config = add_virtual_networking(config)

    if custom_subst_wasm:
        (node_dir / 'docker/leap/contracts/eosio.evm/custom'
        ).mkdir(exist_ok=True, parents=True)

        copyfile(
            custom_subst_wasm,
            node_dir / 'docker/leap/contracts/eosio.evm/custom/custom.wasm'
        )
        config['nodeos']['ini']['subst'] = {}
        config['nodeos']['ini']['subst']['eosio.evm'] = '/opt/eosio/bin/contracts/eosio.evm/custom/custom.wasm'

    if custom_nodeos_tar:
        tar_path = Path(custom_nodeos_tar)
        extensionless_path = Path(tar_path.stem).stem

        bin_name = str(extensionless_path)

        host_config_path = node_dir / 'docker/leap/config'

        with tarfile.open(custom_nodeos_tar, 'r:gz') as file:
            file.extractall(path=host_config_path)

        binary = f'{bin_name}/usr/local/bin/nodeos'

        assert (host_config_path / binary).is_file()

        config['nodeos']['nodeos_bin'] = '/root/' + binary

    if from_snap:
        if from_snap_file:
            raise ValueError(
                'You cannot specify both from_snapshot and from_snapshot_file'
            )

        chain_name = config['telos-evm-rpc']['elastic_prefix']

        if ('mainnet' not in chain_name and
            'testnet' not in chain_name):
            raise ValueError(
                'from_snaphost should only be used against '
                'mainnet or testnet nodes'
            )

        chain_type = 'mainnet' if 'mainnet' in chain_name else 'testnet'

        nodeos_conf_dir = node_dir / 'docker'
        nodeos_conf_dir /= config['nodeos']['docker_path']
        nodeos_conf_dir /= config['nodeos']['conf_dir']
        nodeos_conf_dir.mkdir(exist_ok=True, parents=True)
        snap_path = download_snapshot(
            nodeos_conf_dir, from_snap,
            network=chain_type, progress=True)

        config['nodeos']['snapshot'] = f'/root/{snap_path.name}'
        config['telosevm-translator']['start_block'] = from_snap
        config['telosevm-translator']['deploy_block'] = from_snap

    if from_snap_file:
        if from_snap:
            raise ValueError(
                'You cannot specify both from_snapshot and from_snapshot_file'
            )

        snap_start_block = from_snap_file['block']
        snap_path = from_snap_file['path']

        nodeos_conf_dir = node_dir / 'docker'
        nodeos_conf_dir /= config['nodeos']['docker_path']
        nodeos_conf_dir /= config['nodeos']['conf_dir']
        nodeos_conf_dir.mkdir(exist_ok=True, parents=True)

        copyfile(
            snap_path,
            nodeos_conf_dir / snap_path.name
        )

        assert (nodeos_conf_dir / snap_path.name).is_file()

        config['nodeos']['snapshot'] = f'/root/{snap_path.name}'
        config['telosevm-translator']['start_block'] = snap_start_block
        config['telosevm-translator']['deploy_block'] = snap_start_block


    client = get_docker_client()

    node_dir.mkdir(parents=True, exist_ok=True)
    if not (node_dir / 'tevmc.json').exists():
        touch_node_dir(node_dir, config, 'tevmc.json')

    else:
        with open(node_dir / 'tevmc.json', 'w+') as uni_conf:
            uni_conf.write(json.dumps(config, indent=4))


    containers = None

    try:
        with TEVMController(
            config,
            root_pwd=node_dir,
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


@pytest.fixture
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
