#!/usr/bin/env python3

import json
import socket
import random

from pathlib import Path

import docker

from leap.sugar import random_string

from .default import local, mainnet, testnet


DEFAULT_DOCKER_LABEL = {'created-by': 'tevmc'}
DEFAULT_FILTER = {'label': DEFAULT_DOCKER_LABEL}

MAX_STATUS_SIZE = 54


def get_config(key, _dict):
    if key in _dict:
        return _dict[key]

    else:
        if '.' in key:
            splt_key = key.split('.')
            return get_config(
                '.'.join(splt_key[1:]),
                _dict[splt_key[0]])

        else:
            raise KeyError(f'{key} not in {_dict.keys()}')


def load_config(location: str, name: str) -> dict[str, dict]:
    target_dir = (Path(location)).resolve()
    config_file = (target_dir / name).resolve()

    with open(config_file, 'r') as config_file:
        return json.loads(config_file.read())


def build_docker_manifest(config: dict) -> list[str]:
    chain_name = config['telos-evm-rpc']['elastic_prefix']
    manifest = []
    for container_name, conf in config.items():
        if 'docker_path' not in conf:
            continue

        try:
            repo, tag = conf['tag'].split(':')
            tag = f'{tag}-{chain_name}'

        except ValueError:
            raise ValueError(
                f'Malformed tag {key}=\'{arg}\','
                f' must be of format \'{repo}:{tag}\'.')

        manifest.append((repo, tag))

    return manifest


def check_docker_manifest(client, manifest: list):
    for repo, tag in manifest:
        try:
            client.images.get(f'{repo}:{tag}')

        except docker.errors.NotFound:
            raise docker.errors.NotFound(
                f'Docker image \'{repo}:{tag}\' is required, please run '
                '\'tevmc build\' to build the required images.'
            )


def randomize_conf_ports(config: dict) -> dict:
    ret = config.copy()

    def get_free_port(tries=10):
        _min = 10000
        _max = 60000

        for _ in range(tries):
            port_num = random.randint(_min, _max)

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                s.bind(("127.0.0.1", port_num))
                s.close()

            except socket.error as e:
                continue

            else:
                return port_num

    def get_free_remote_addr():
        return f'0.0.0.0:{get_free_port()}'

    # redis
    ret['redis']['port'] = get_free_port()

    # elasticsearch
    elastic_addr = get_free_remote_addr()
    ret['elasticsearch']['host'] = elastic_addr

    # kibana
    ret['kibana']['port'] = get_free_port()

    # nodeos
    nodeos_http_port = get_free_port()
    state_history_port = get_free_port()
    ret['nodeos']['ini']['http_addr'] = f'0.0.0.0:{nodeos_http_port}'
    ret['nodeos']['ini']['p2p_addr'] = f'0.0.0.0:{get_free_port()}'
    ret['nodeos']['ini']['history_endpoint'] = f'0.0.0.0:{state_history_port}'

    # telos-evm-rpc
    idx_ws_port = get_free_port()
    ret['telos-evm-rpc']['indexer_websocket_port'] = idx_ws_port
    ret['telos-evm-rpc']['indexer_websocket_uri'] = f'ws://127.0.0.1:{idx_ws_port}/evm'

    ret['telos-evm-rpc']['rpc_websocket_port'] = get_free_port()

    ret['telos-evm-rpc']['api_port'] = get_free_port()

    if '127.0.0.1' in ret['telos-evm-rpc']['remote_endpoint']:
        ret['telos-evm-rpc']['remote_endpoint'] = f'http://127.0.0.1:{nodeos_http_port}/evm'

    # daemon control api_port
    ret['daemon']['port'] = get_free_port();

    return ret

def randomize_conf_creds(config: dict) -> dict:
    ret = config.copy()

    ret['elasticsearch']['user'] = random_string(size=16)
    ret['elasticsearch']['elastic_pass'] = random_string(size=32)
    ret['elasticsearch']['pass'] = random_string(size=32)

    return ret

def add_virtual_networking(config: dict) -> dict:
    ret = config.copy()

    ips = [
        f'192.168.123.{i}'
        for i in range(2, 9)
    ]

    # redis
    ret['redis']['virtual_ip'] = ips[0]

    # elastic
    ret['elasticsearch']['virtual_ip'] = ips[1]

    # kibana
    ret['kibana']['virtual_ip'] = ips[2]

    # nodeos
    ret['nodeos']['virtual_ip'] = ips[3]

    # beats
    ret['beats']['virtual_ip'] = ips[4]

    # translator
    ret['telosevm-translator']['virtual_ip'] = ips[5]

    # rpc
    ret['telos-evm-rpc']['virtual_ip'] = ips[6]
    ret['telos-evm-rpc']['api_host'] = ips[6]
    indexer_ws_port = ret['telos-evm-rpc']['indexer_websocket_port']
    ret['telos-evm-rpc']['indexer_websocket_uri'] = f'ws://{ips[5]}:{indexer_ws_port}/evm'

    return ret
