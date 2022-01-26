#!/usr/bin/env python3

import os
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
from ..config import *

from .cli import cli, get_docker_client


@cli.command()
@click.option(
    '--pid', default='tevmc.pid',
    help='Path to lock file for daemon')
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.option(
    '--logpath', default='tevmc.log',
    help='Log file path.')
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
    config,
    logpath,
    loglevel,
    target_dir,
    docker_timeout
):
    """Bring tevmc daemon up.
    """
    try:
        config = load_config(target_dir, config)

    except FileNotFoundError:
        print('Config not found.')
        sys.exit(1)

    prev_run_pid = None
    try:
        with open(target_dir + '/.prev', 'r') as prev_pid_file:
            prev_run_pid = int(prev_pid_file.read())

    except FileNotFoundError:
        pass
        
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
    for container_name, conf in config.items():
        if 'docker_path' not in conf:
            continue

        try:
            repo, tag = conf['tag'].split(':')
            tag = f'{tag}-{config["hyperion"]["chain"]["name"]}'

        except ValueError:
            logger.critical(
                f'Malformed tag {key}=\'{arg}\','
                f' must be of format \'{repo}:{tag}\'.')
            sys.exit(1)

        manifest.append((repo, tag))

    logger.info(
        f'container manifest: {json.dumps(manifest, indent=4)}')

    # check images are present in local docker repo
    client = get_docker_client(timeout=docker_timeout)
    for repo, tag in manifest:
        try:
            client.images.get(f'{repo}:{tag}')

        except docker.errors.NotFound:
            logger.critical(f'docker image {repo}:{tag} not present, abort.')
            print(
                f'Docker image \'{repo}:{tag}\' is required, please run '
                '\'tevmc build\' to build the required images.'
            )
            sys.exit(1)

    # main daemon thread
    def wait_exit_forever():
        if not Path('.prev').is_file():
            with open('.prev', 'w+') as prev_pid_file:
                prev_pid_file.write(
                    str(os.getpid()) + '\n')

        try:
            with TEVMController(
                config,
                logger=logger,
                prev_pid=prev_run_pid
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
        keep_fds=keep_fds,
        chdir=target_dir)

    daemon.start()

