#!/usr/bin/env python3



import click
import docker
import requests


from ..config import (
    DEFAULT_NETWORK_NAME, DEFAULT_VOLUME_NAME
)

from .cli import cli



@cli.command()
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
    '--hyperion-indexer-name', default='hyperion-indexer',
    help='Hyperion indexer container name.')
@click.option(
    '--hyperion-api-name', default='hyperion-api',
    help='Hyperion api container name.')
def clean(**kwargs):
    client = docker.from_env(timeout=10)
    for arg, val in kwargs.items():
        try:
            container = client.containers.get(val)
            if container.status == 'running':
                print(f'Container {val} is running, killing... ', end='', flush=True)
                container.kill()
                print('done.')

            container.remove()

        except requests.exceptions.ReadTimeout:
            print('timeout!')

        except docker.errors.NotFound:
            print(f'{val} not found!')

    client = docker.from_env(timeout=120)

    print(
        f'Delete containers created by tevmc... ', end='', flush=True)
    client.containers.prune(
        filters={'label': {'created-by': 'tevmc'}})
    print('done.')

    print(
        f'Delete \'{DEFAULT_NETWORK_NAME}\' network... ', end='', flush=True)
    client.networks.prune(
        filters={'label': {'created-by': 'tevmc'}})
    print('done.')

    print(f'Delete \'{DEFAULT_VOLUME_NAME}\' volume... ', end='', flush=True)
    client.volumes.prune(
        filters={'label': {'created-by': 'tevmc'}})
    print('done.')
