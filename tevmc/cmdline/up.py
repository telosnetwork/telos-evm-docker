#!/usr/bin/env python3

from copy import deepcopy
import os
import shutil
import sys
import json
import logging

from pathlib import Path

import click
import requests

from tevmc.cmdline.build import patch_config
from tevmc.utils import deep_dict_equal

from ..config import *

from .cli import cli


@cli.command()
@click.option(
    '--pid', default='tevmc.pid',
    help='Path to lock file for daemon')
@click.option(
    '--services',
    default=json.dumps([
        'redis',
        'elastic',
        'kibana',
        'nodeos',
        'indexer',
        'rpc',
    ]),
    help='Services to launch')
@click.option(
    '--wait/--no-wait', default=False,
    help='Wait until caught up to sync before launching RPC api.')
@click.option(
    '--sync/--head', default=True,
    help='Sync from chain start or from head.')
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.option(
    '--loglevel', default='info',
    help='Provide logging level. Example --loglevel debug, default=warning')
@click.option(
    '--target-dir', default='.',
    help='target')
@click.option(
    '--conf-upgrade/--no-conf-upgrade', default=None,
    help='Perform or ignore posible config upgrade.')
def up(
    pid,
    services,
    wait,
    sync,
    config,
    loglevel,
    target_dir,
    conf_upgrade
):
    """Bring tevmc daemon up.
    """
    from ..tevmc import TEVMController

    config_filename = config
    try:
        config = load_config(target_dir, config)

    except FileNotFoundError:
        print('Config not found.')
        sys.exit(1)

    # optionally upgrade conf
    up_config = None
    cmp_config = deepcopy(config)
    if 'metadata' in cmp_config:
        del cmp_config['metadata']
    diffs = None
    if 'local' in config['telos-evm-rpc']['elastic_prefix']:
        up_config, diffs = patch_config(local.default_config, cmp_config)

    elif 'testnet' in config['telos-evm-rpc']['elastic_prefix']:
        up_config, diffs = patch_config(testnet.default_config, cmp_config)

    elif 'mainnet' in config['telos-evm-rpc']['elastic_prefix']:
        up_config, diffs = patch_config(mainnet.default_config, cmp_config)

    # if config upgrade is posible and flag not passed
    # print new conf and exit.
    if (up_config and
        not deep_dict_equal(up_config, cmp_config)):

        if conf_upgrade != None:
            if conf_upgrade:
                # backup old conf
                config_path = Path(target_dir) / config_filename
                backup_path = config_path.with_name(f'{config_path.name}.backup')

                if backup_path.is_file():
                    print('Backup file alredy exist, please move it before re-doing config upgrade...')
                    sys.exit(3)

                shutil.copy(config_path, backup_path)

                # write upgraded config
                with open(config_path, 'w+') as conf:
                    conf.write(json.dumps(up_config, indent=4))

                config = up_config

            else:
                print(json.dumps(up_config, indent=4))
                print(f'Config upgrade posible and --conf-upgrade not passed!')
                for diff in diffs:
                    print(diff)
                sys.exit(2)

    if Path(pid).resolve().exists():
        print('Daemon pid file exists. Abort.')
        sys.exit(1)

    fmt = logging.Formatter(
        fmt='%(asctime)s:%(levelname)s:%(message)s',
        datefmt='%H:%M:%S'
    )
    loglevel = loglevel.upper()
    logger = logging.getLogger('tevmc')
    logger.setLevel(loglevel)
    logger.propagate = False

    # config logging to stdout
    oh = logging.StreamHandler(sys.stdout)
    oh.setLevel(loglevel)
    oh.setFormatter(fmt)
    logger.addHandler(oh)

    if isinstance(services, str):
        try:
            services = json.loads(services)

        except json.JSONDecodeError:
            print('--services value must be a json list encoded in a string')
            sys.exit(1)

    with open(pid, 'w+') as pidfile:
        pidfile.write(str(os.getpid()))

    try:
        with TEVMController(
            config,
            logger=logger,
            wait=wait,
            services=services,
            from_latest=not sync
        ) as _tevmc:
            logger.critical('control point reached')
            try:
                _tevmc.serve_api()

            except KeyboardInterrupt:
                logger.warning('interrupt catched.')

    except requests.exceptions.ReadTimeout:
        logger.critical(
            'docker timeout! usually means system hung, '
            'please await tear down or run \'tevmc clean\''
            'to cleanup envoirment.')
