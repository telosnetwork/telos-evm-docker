#!/usr/bin/env python3

import sys

import click
import docker

from py_eosio.sugar import (
    docker_wait_process,
    docker_open_process
)

from .cli import cli


@cli.command()
@click.option(
    '--logpath', default='/tmp/tevmc.log',
    help='Log file path.')
@click.argument('source')
def stream(logpath, source):
    """Stream logs from either the tevmc daemon or a container.
    """
    client = docker.from_env()
    try:
        if source == 'daemon':
            with open(logpath, 'r') as logfile:
                line = ''
                while 'Stopping daemon.' not in line:
                    line = logfile.readline()
                    print(line, end='', flush=True)

        elif source == 'eosio_nodeos':
            try:
                node = client.containers.get('eosio_nodeos')

            except docker.errors.NotFound:
                print('Eosio container not found!')
                sys.exit(1)

            exec_id, exec_stream = docker_open_process(
                client, node,
                ['/bin/bash', '-c',
                'tail -f /root/nodeos.log'])

            for chunk in exec_stream:
                msg = chunk.decode('utf-8')
                print(msg, end='', flush=True)

        elif source == 'hyperion-indexer-serial':
            try:
                hyperion = client.containers.get('hyperion-indexer')

            except docker.errors.NotFound:
                print('Hyperion container not found!')
                sys.exit(1)

            exec_id, exec_stream = docker_open_process(
                client, hyperion, ['ls', '/hyperion-history-api/logs'])

            ec, out = docker_wait_process(client, exec_id, exec_stream)
            
            chain_name = out.rstrip()

            exec_id, exec_stream = docker_open_process(
                client, hyperion,
                ['/bin/bash', '-c',
                f'tail -f /hyperion-history-api/logs/{chain_name}/deserialization_errors.log'])

            for chunk in exec_stream:
                msg = chunk.decode('utf-8')
                print(msg, end='', flush=True)

        else:
            try:
                container = client.containers.get(source)
                for chunk in container.logs(stream=True):
                    msg = chunk.decode('utf-8')
                    print(msg, end='', flush=True)

            except docker.errors.NotFound:
                print(f'Container \"{source}\" not found!')

    except KeyboardInterrupt:
        print('Interrupted.')
