#!/usr/bin/env python3

import sys
import json

from string import Template
from typing import Dict
from pathlib import Path
from distutils.dir_util import copy_tree

import click

from .cli import cli
from ..config import (
    local, testnet, mainnet,
    randomize_conf_ports, randomize_conf_creds,
    add_virtual_networking
)


source_dir = Path(__file__).parent.parent
template_dir = (source_dir / 'docker').resolve(strict=False)


def load_docker_templates() -> Dict[str, Template]:
    templ = {}
    for node in (template_dir).glob('**/*'):
        if node.is_file():
            with open(node, 'r') as templ_file:
                try:
                    key = '/'.join(node.parts[-3:])
                    templ[key] = Template(templ_file.read())
                except UnicodeDecodeError:
                    pass

    return templ


def touch_node_dir(target_dir: Path, conf: dict, fname: str):
    # dump default config file
    with open(target_dir / fname, 'w+') as uni_conf:
        uni_conf.write(json.dumps(conf, indent=4))

    # copy new directory tree template
    copy_tree(
        str(template_dir),
        str(target_dir / 'docker'))

    # create logs dir
    (target_dir / 'logs').mkdir(exist_ok=True)


@cli.command()
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.option(
    '--target-dir', default='.',
    help='target')
@click.option(
    '--random-creds/--default-creds', default=False,
    help='Randomize elasticsearch credentials.')
@click.option(
    '--random-ports/--default-ports', default=False,
    help='Randomize port and node name, useful to boot '
         'multiple nodes on same host.')
@click.argument('chain-name')
def init(config, target_dir, chain_name, random_creds, random_ports):

    if not template_dir.is_dir():
        print('Template directory not found.')
        sys.exit(1)

    target_dir = (Path(target_dir)).resolve(strict=False)

    if not target_dir.is_dir():
        print('Target directory not found.')
        sys.exit(1)

    conf = {}
    if 'local' in chain_name:
        conf = local.default_config

    elif 'testnet' in chain_name:
        conf = testnet.default_config

    elif 'mainnet' in chain_name:
        conf = mainnet.default_config

    if random_ports:
        conf = randomize_conf_ports(conf)

    if random_creds:
        conf = randomize_conf_creds(conf)

    if sys.platform == 'darwin':
        conf = add_virtual_networking(conf)

    target_dir = target_dir / chain_name
    target_dir.mkdir(parents=True, exist_ok=True)

    touch_node_dir(target_dir, conf, config)

