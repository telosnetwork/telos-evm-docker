#!/usr/bin/env python3

import sys

import click
import docker

from py_eosio.sugar import (
    docker_wait_process,
    docker_open_process
)

from .cli import cli, get_docker_client


@cli.command()
@click.option(
    '--pid', default='tevmc.pid',
    help='Path to lock file for daemon')
@click.option(
    '--logpath', default='tevmc.log',
    help='Log file path.')
@click.option(
    '--target-dir', default='.',
    help='target')
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.argument('source')
def stream(pid, logpath, target_dir, config, source):
    """Stream logs from either the tevmc daemon or a container.
    """
    client = get_docker_client()

    try:
        with open(pid, 'r') as pidfile:
            pid = int(pidfile.read())

    except FileNotFoundError:
        print('daemon not running.')


    try:
        if source == 'daemon':
            with open(logpath, 'r') as logfile:
                line = ''
                while True:
                    try:
                        line = logfile.readline()
                        print(line, end='', flush=True)

                    except UnicodeDecodeError:
                        pass

        else:
            try:
                container = client.containers.get(f'{source}-{pid}')

            except docker.errors.NotFound:
                print(f'Container \"{source}\" not found!')
                sys.exit(1)

            for chunk in container.logs(stream=True):
                msg = chunk.decode('utf-8')
                print(msg, end='', flush=True)

    except KeyboardInterrupt:
        print('Interrupted.')
