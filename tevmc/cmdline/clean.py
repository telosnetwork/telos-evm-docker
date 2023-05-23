#!/usr/bin/env python3

import sys
import time
import click
import docker
import psutil
import requests

from ..config import *
from .cli import cli, get_docker_client


@cli.command()
@click.option(
    '--pid', default='tevmc.pid',
    help='Path to lock file for daemon')
@click.option(
    '--target-dir', default='.',
    help='target')
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
def clean(pid, target_dir, config):
    """Cleanup docker envoirment, kill all running containers,
    remove them, and prune networks and volumes.
    """
    try:
        config = load_config(target_dir, config)

    except FileNotFoundError:
        print('Config not found.')
        sys.exit(1)

    print('Stopping daemon... ', end='', flush=True)
    try:
        with open(pid, 'r') as pidfile:
            pid = int(pidfile.read())

        tevmcd = psutil.Process(pid)
        tevmcd.terminate()
        tevmcd.wait()
        print('done.')

    except FileNotFoundError:
        print('daemon not running.')
        return

    client = get_docker_client(timeout=10)

    for val in [
        f'{conf["name"]}-{pid}'
        for name, conf in config.items()
    ]:
        while True:
            try:
                container = client.containers.get(val)
                if container.status == 'running':
                    print(f'Container {val} is running, killing... ', end='', flush=True)
                    container.kill()
                    print('done.')

                container.remove()

            except docker.errors.APIError as err:
                if 'already in progress' in str(err):
                    time.sleep(0.1)
                    continue

            except requests.exceptions.ReadTimeout:
                print('timeout!')

            except docker.errors.NotFound:
                print(f'{val} not found!')

            break
