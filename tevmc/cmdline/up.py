#!/usr/bin/env python3

import os
import sys
import json
import logging

from pathlib import Path

import click
import docker
import requests

from ..config import *

from .cli import cli, get_docker_client


@cli.command()
@click.option(
    '--pid', default='tevmc.pid',
    help='Path to lock file for daemon')
@click.option(
    '--services',
    default=[
        'redis',
        'elastic',
        'kibana',
        'nodeos',
        'indexer',
        'rpc',
    ],
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
    '--docker-timeout', default=60,
    help='Docker client command timeout.')
def up(
    pid,
    services,
    wait,
    sync,
    config,
    loglevel,
    target_dir,
    docker_timeout
):
    """Bring tevmc daemon up.
    """
    from ..tevmc import TEVMController

    try:
        config = load_config(target_dir, config)

    except FileNotFoundError:
        print('Config not found.')
        sys.exit(1)

    if Path(pid).resolve().exists():
        print('Daemon pid file exists. Abort.')
        sys.exit(1)

    # simple build check
    if 'metadata' not in config:
        print(
            'No metadata in temvc.json, please build '
            'with \'tevmc build\' before running.')
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

    # create image manifest ie images needed to run daemon
    try:
        manifest = build_docker_manifest(config)

    except ValueError as err:
        print(err.message)
        sys.exit(1)

    logger.info(
        f'container manifest: {json.dumps(manifest, indent=4)}')

    # check images are present in local docker repo
    client = get_docker_client(timeout=docker_timeout)
    try:
        check_docker_manifest(client, manifest)

    except docker.errors.NotFound as err:
        logger.critical(err.message)
        sys.exit(1)

    with open(pid, 'w+') as pidfile:
        pidfile.write(os.getpid())

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
