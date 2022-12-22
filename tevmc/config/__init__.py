#!/usr/bin/env python3

import json
import errno
import socket
import random

from typing import Dict, List, Any
from pathlib import Path

import docker

from py_eosio.sugar import random_string

from .default import local, testnet, mainnet


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


def load_config(location: str, name: str) -> Dict[str, Dict]:
    target_dir = (Path(location)).resolve()
    config_file = (target_dir / name).resolve()

    with open(config_file, 'r') as config_file:
        return json.loads(config_file.read())


def build_docker_manifest(config: Dict) -> List[str]:
    manifest = []
    for container_name, conf in config.items():
        if 'docker_path' not in conf:
            continue

        try:
            repo, tag = conf['tag'].split(':')
            tag = f'{tag}-{config["hyperion"]["chain"]["name"]}'

        except ValueError:
            raise ValueError(
                f'Malformed tag {key}=\'{arg}\','
                f' must be of format \'{repo}:{tag}\'.')

        manifest.append((repo, tag))

    return manifest


def check_docker_manifest(client, manifest: List):
    for repo, tag in manifest:
        try:
            client.images.get(f'{repo}:{tag}')

        except docker.errors.NotFound:
            raise docker.errors.NotFound(
                f'Docker image \'{repo}:{tag}\' is required, please run '
                '\'tevmc build\' to build the required images.'
            )


def randomize_conf_ports(config: Dict) -> Dict:
    ret = config.copy()

    def get_free_port(tries=10):
        _min = 10000
        _max = 60000
        found = False
        
        for i in range(tries):
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

    def get_free_local_addr():
        return f'localhost:{get_free_port()}'

    def get_free_remote_addr():
        return f'0.0.0.0:{get_free_port()}'

    # redis
    ret['redis']['port'] = get_free_port()

    # rabbitmq
    ret['rabbitmq']['node_name'] = f'{random_string(size=20)}@localhost'

    ret['rabbitmq']['host'] = get_free_local_addr()
    ret['rabbitmq']['api'] = get_free_local_addr()
    ret['rabbitmq']['dist_port'] = get_free_port() 
    ret['rabbitmq']['prometheus_port'] = get_free_port()

    # elasticsearch
    elastic_addr = get_free_local_addr()
    ret['elasticsearch']['host'] = elastic_addr
    ret['elasticsearch']['ingest_nodes'] = [elastic_addr]

    # kibana
    ret['kibana']['port'] = get_free_port()

    # nodeos
    nodeos_http_port = get_free_port()
    state_history_port = get_free_port()
    ret['nodeos']['ini']['http_addr'] = f'0.0.0.0:{nodeos_http_port}'
    ret['nodeos']['ini']['p2p_addr'] = f'0.0.0.0:{get_free_port()}'
    ret['nodeos']['ini']['history_endpoint'] = f'0.0.0.0:{state_history_port}'

    # hyperion
    ret['hyperion']['chain']['http'] = f'http://localhost:{nodeos_http_port}'
    ret['hyperion']['chain']['ship'] = f'ws://localhost:{state_history_port}'
    
    hyperion_api_port = get_free_port()
    ret['hyperion']['chain']['router_port'] = get_free_port()

    idx_ws_port = get_free_port()

    ret['hyperion']['chain']['telos-evm'][
        'nodeos_read'] = f'http://localhost:{nodeos_http_port}'

    ret['hyperion']['chain']['telos-evm'][
        'indexerWebsocketPort'] = idx_ws_port

    ret['hyperion']['chain']['telos-evm'][
        'indexerWebsocketUri'] = f'ws://127.0.0.1:{idx_ws_port}/evm'

    ret['hyperion']['chain']['telos-evm'][
        'rpcWebsocketPort'] = get_free_port()

    ret['hyperion']['api']['server_port'] = hyperion_api_port

    return ret

def randomize_conf_creds(config: Dict) -> Dict:
    ret = config.copy()

    # random credentials
    ret['rabbitmq']['user'] = random_string(size=16)
    ret['rabbitmq']['pass'] = random_string(size=32)

    ret['elasticsearch']['user'] = random_string(size=16)
    ret['elasticsearch']['elastic_pass'] = random_string(size=32)
    ret['elasticsearch']['pass'] = random_string(size=32)

    return ret
