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
    '--pid', default='/tmp/tevmc.pid',
    help='Path to lock file for daemon')
@click.option(
    '--redis-name', default='redis',
    help='Redis container name.')
@click.option(
    '--rabbitmq-name', default='rabbitmq',
    help='Rabbitmq container name.')
@click.option(
    '--elasticsearch-name', default='elasticsearch',
    help='Elastic search container name.')
@click.option(
    '--kibana-name', default='kibana',
    help='Kibana container name.')
@click.option(
    '--eosio-name', default='eosio_nodeos',
    help='Eosio node container name.')
@click.option(
    '--beats', default='beats',
    help='Beats container name.')
@click.option(
    '--hyperion-indexer-name', default='hyperion-indexer',
    help='Hyperion indexer container name.')
@click.option(
    '--hyperion-api-name', default='hyperion-api',
    help='Hyperion api container name.')
def clean(pid, **kwargs):
    """Cleanup docker envoirment, kill all running containers,
    remove them, and prune networks and volumes.
    """

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

    client = get_docker_client(timeout=10)

    for arg, val in kwargs.items():
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

    client = docker.from_env(timeout=120)

    print(
        f'Delete containers created by tevmc... ', end='', flush=True)
    client.containers.prune(
        filters=DEFAULT_FILTER)
    print('done.')

    print(
        f'Delete \'{DEFAULT_NETWORK_NAME}\' network... ', end='', flush=True)
    client.networks.prune(
        filters=DEFAULT_FILTER)
    print('done.')

    print(f'Delete created volumes... ', end='', flush=True)
    client.volumes.prune(
        filters=DEFAULT_FILTER)

    for volume_name in [
        EOSIO_VOLUME_NAME,
        HYPERION_API_LOG_VOLUME,
        HYPERION_INDEXER_LOG_VOLUME
    ]:
        try:
            volume = client.volumes.get(volume_name)
            volume.remove(force=True)

        except docker.errors.NotFound:
            pass

    print('done.')
