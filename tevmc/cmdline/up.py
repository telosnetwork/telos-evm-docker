#!/usr/bin/env python3

import sys
import json
import time
import logging

from pathlib import Path

import click
import docker
import requests

from daemonize import Daemonize

from ..tevmc import TEVMController

from .cli import cli


@cli.command()
@click.option(
    '--pid', default='/tmp/tevmc.pid',
    help='Path to lock file for daemon')
@click.option(
    '--port', default=6666,
    help='Port to listen for termination.')
@click.option(
    '--logpath', default='/tmp/tevmc.log',
    help='Log file path.')
@click.option(
    '--loglevel', default='warning',
    help='Provide logging level. Example --loglevel debug, default=warning')
@click.option(
    '--snapshot', default=None,
    help='Snapshot location inside container.')
@click.option(
    '--chain-name', default='telos-local-testnet',
    help='Chain name for hyperion to index.')
@click.option(
    '--release-evm/--debug-evm', default=True,
    help='Deploy release/debug evm contract.')
@click.option(
    '--docker-timeout', default=60,
    help='Docker client command timeout.')
@click.option(
    '--redis-tag', default='redis:5.0.9-buster',
    help='Redis container image tag.')
@click.option(
    '--rabbitmq-tag', default='rabbitmq:3.8.3-management',
    help='Rabbitmq container image tag.')
@click.option(
    '--elasticsearch-tag', default='docker.elastic.co/elasticsearch/elasticsearch:7.13.2',
    help='Elastic search container image tag.')
@click.option(
    '--kibana-tag', default='docker.elastic.co/kibana/kibana:7.7.1',
    help='Kibana container image tag.')
@click.option(
    '--eosio-tag', default='eosio:2.1.0-evm',
    help='Eosio nodeos container image tag.')
@click.option(
    '--hyperion-tag', default='telos.net/hyperion:0.1.0',
    help='Hyperion container image tag.')
def up(
    pid,
    port,
    logpath,
    loglevel,
    snapshot,
    chain_name,
    release_evm,
    docker_timeout,
    **kwargs  # leave container tags to kwargs 
):
    """Bring tevmc daemon up.
    """
    if Path(pid).resolve().exists():
        print('daemon pid file exists. abort.')
        sys.exit(1)

    # config logging to file
    loglevel = loglevel.upper()

    fmt = logging.Formatter(
        fmt='%(asctime)s:%(levelname)s:%(message)s',
        datefmt='%H:%M:%S'
    )

    logger = logging.getLogger('tevmc')
    logger.setLevel(loglevel)
    logger.propagate = False
    fh = logging.FileHandler(logpath, 'w')
    fh.setLevel(loglevel)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    keep_fds = [fh.stream.fileno()]

    # create image manifest ie images needed to run daemon 
    manifest = []
    for key, arg in kwargs.items():
        try:
            repo, tag = arg.split(':')

        except ValueError:
            logger.critical(
                f'Malformed tag {key}=\'{arg}\','
                f' must be of format \'{repo}:{tag}\'.')
            sys.exit(1)

        manifest.append((repo, tag))

    logger.info(
        f'container manifest: {json.dumps(manifest, indent=4)}')

    # check images are present in local docker repo
    client = docker.from_env(timeout=docker_timeout)
    for repo, tag in manifest:
        try:
            client.images.get(f'{repo}:{tag}')

        except docker.errors.NotFound:
            logger.critical(f'docker image {repo}:{tag} not present, abort.')
            print(
                f'Docker image \'{repo}:{tag}\' is required, please run '
                '\'tevmc pull\' to download the required images.'
            )
            sys.exit(1)

    # main daemon thread
    def wait_exit_forever():
        try:
            with TEVMController(
                logger=logger,
                debug_evm=not release_evm,
                chain_name=chain_name,
                snapshot=snapshot,
                **kwargs
            ) as tevm:
                logger.critical('control point reached')
                try:
                    while True:
                        time.sleep(90)

                except KeyboardInterrupt:
                    logger.warning('interrupt catched.')

        except requests.exceptions.ReadTimeout:
            logger.critical(
                'docker timeout! usually means system hung, '
                'please await tear down or run \'tevmc clean\''
                'to cleanup envoirment.')
            
    # daemonize
    daemon = Daemonize(
        app='tevmc',
        pid=pid,
        action=wait_exit_forever,
        keep_fds=keep_fds)

    daemon.start()

