#!/usr/bin/env python3

import os

import pytest
import docker
import logging
import requests

from tevmc import TEVMController
from tevmc.config import (
    local,
    build_docker_manifest
)
from tevmc.cmdline.init import touch_node_dir
from tevmc.cmdline.build import perform_docker_build
from tevmc.cmdline.clean import clean
from tevmc.cmdline.cli import get_docker_client


@pytest.fixture(scope='session')
def tevmc(tmp_path_factory):

    client = get_docker_client()
    config = local.default_config

    tmp_path = tmp_path_factory.getbasetemp() / 'pytest-local'
    manifest = build_docker_manifest(config)

    tmp_path.mkdir(parents=True, exist_ok=True)
    touch_node_dir(tmp_path, config, 'tevmc.json')
    perform_docker_build(
        tmp_path, config, logging)

    try:
        with TEVMController(
            config,
            root_pwd=tmp_path
        ) as _tevmc:
            yield _tevmc

    except BaseException:
        pid = os.getpid()

        client = get_docker_client(timeout=10)

        containers = []
        for name, conf in config.items():
            if 'name' in conf:
                containers.append(f'{conf["name"]}-{pid}')


        containers.append(
            f'{local.default_config["hyperion"]["indexer"]["name"]}-{pid}')
        containers.append(
            f'{local.default_config["hyperion"]["api"]["name"]}-{pid}')

        for val in containers:
            while True:
                try:
                    container = client.containers.get(val)
                    if container.status == 'running':
                        print(f'Container {val} is running, killing... ', end='', flush=True)
                        container.kill()
                        print('done.')

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
