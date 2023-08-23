#!/usr/bin/env python3

import time
import json
import logging

from pathlib import Path

import click
import docker
from docker.types import Mount

from leap.sugar import download_snapshot
from tevmc.cmdline.build import build_service
from tevmc.config import load_config
from tevmc.testing.database import ElasticDataEmptyError, ElasticDriver

from .cli import cli


def perform_data_repair(config_path, progress=True):
    from tevmc.tevmc import TEVMController

    root_pwd = config_path.parent.resolve()
    config = load_config(str(root_pwd), config_path.name)

    chain_name = config['telos-evm-rpc']['elastic_prefix']

    if ('mainnet' not in chain_name and
        'testnet' not in chain_name):
        raise ValueError(
            'tevmc repair should only be run against '
            'mainnet or testnet nodes'
        )

    chain_type = 'mainnet' if 'mainnet' in chain_name else 'testnet'

    logging.info('repairing elastic data...')

    with TEVMController(
        config, root_pwd=root_pwd, services=['elastic']):
        time.sleep(5)
        es = ElasticDriver(config)
        last_valid_nums = es.repair_data()

    logging.info(f'done, last valid blocks {last_valid_nums}')
    logging.info('downloading closest snapshot...')

    docker_dir = root_pwd / 'docker'
    nodeos_conf_dir = docker_dir
    nodeos_conf_dir /= config['nodeos']['docker_path']
    nodeos_conf_dir /= config['nodeos']['conf_dir']

    snap_path = download_snapshot(
        nodeos_conf_dir, last_valid_nums[0],
        network=chain_type, progress=progress)

    logging.info('updating tevmc.json...')

    config['nodeos']['snapshot'] = f'/root/{snap_path.name}'

    config['telosevm-translator']['start_block'] = last_valid_nums[0]

    with open(config_path, 'w+') as uni_conf:
        uni_conf.write(json.dumps(config, indent=4))

    logging.info('done, deleting dirty nodeos data...')

    nodeos_data_path = config['nodeos']['docker_path']
    nodeos_data_path += '/' + config['nodeos']['data_dir_host']

    # delete file using docker cause usually has root perms
    client = docker.from_env()
    client.containers.run(
        'bash',
        f'bash -c \"rm -rf /root/target/docker/{nodeos_data_path}\"',
        remove=True,
        mounts=[Mount('/root/target', str(docker_dir.parent), 'bind')]
    )

    assert not (docker_dir / nodeos_data_path).is_dir()

    logging.info('rebuild nodeos image...')

    build_service(
        root_pwd, 'nodeos', config)


@cli.command()
@click.option(
    '--config', default='tevmc.json',
    help='Path to config file.')
def repair(config):
    try:
        perform_data_repair(Path(config))

    except ElasticDataEmptyError:
        logging.info('no data to repair')
