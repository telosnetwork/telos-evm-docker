#!/usr/bin/env python3

import sys
import shutil

from pathlib import Path

import click

from tevmc.cmdline.repair import perform_data_repair
from tevmc.cmdline.up import open_node_from_dir

from .cli import cli

from .init import touch_node_dir

from ..config import (
    local, testnet, mainnet,
)

import pdbp


def migrate_node(
    source_dir: str | Path,
    target_dir: str | Path
):
    print('Migrating node...')
    source_dir = (Path(source_dir)).resolve(strict=False)

    if not source_dir.is_dir():
        print('Target directory not found.')
        sys.exit(1)

    chain_name = str(source_dir)
    chain_type = 'unknown'

    conf = {}
    if 'local' in chain_name:
        chain_type = 'local'
        conf = local.default_config

    elif 'testnet' in chain_name:
        chain_type = 'testnet'
        conf = testnet.default_config

    elif 'mainnet' in chain_name:
        chain_type = 'mainnet'
        conf = mainnet.default_config

    print(f'Detected node type {chain_type}')

    target_dir = (Path(target_dir)).resolve(strict=False)
    target_dir.mkdir()

    shutil.copy(source_dir / 'tevmc.json', target_dir / 'tevmc.json')

    touch_node_dir(target_dir, conf, 'tevmc.json')

    with open_node_from_dir(
        target_dir,
        services=[]
    ):
        ...

    print(f'Created new node dir at {target_dir}')

    elastic_data_dir_src: Path = source_dir / 'docker/elasticsearch/data'
    elastic_data_dir_dst: Path = target_dir / 'docker/elasticsearch/data'

    if elastic_data_dir_src.is_dir():
        print(f'Detected exisitng elastic data!')
        resp = input(f'Do you wish to move elastic data to new node?: y/n')
        if resp == 'y':
            shutil.rmtree(elastic_data_dir_dst)
            shutil.move(elastic_data_dir_src, elastic_data_dir_dst)
            print(f'Moved elastic data from {elastic_data_dir_src} to {elastic_data_dir_dst}.')
        elif resp == 'n':
            print('Skipping elastic data transfer.')

        else:
            raise ValueError('expected \'y\' or \'n\'')

    else:
        print('No elastic data to migrate!')
        sys.exit(1)

    print(f'Tevmc will validate evm data and find an apropiate snapshot for nodeos')

    perform_data_repair(target_dir / 'tevmc.json')


@cli.command()
@click.argument('source', type=str)
@click.argument('destination', type=str)
def migrate(source, destination):
    migrate_node(source, destination)
