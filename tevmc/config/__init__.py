#!/usr/bin/env python3

import json

from typing import Dict, List, Any
from pathlib import Path

import docker

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

