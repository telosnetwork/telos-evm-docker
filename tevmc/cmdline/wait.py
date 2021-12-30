#!/usr/bin/env python3

import time
import logging

import click
import docker
import requests

from .cli import cli


@cli.command()
@click.argument('block-num')
def wait_block(block_num):
    """Await for block indexing.
    """
    client = docker.from_env()
    stop = False

    while not stop:
        try:
            hyperion = client.containers.get('hyperion-indexer')
            for chunk in hyperion.logs(stream=True):
                msg = chunk.decode('utf-8')
                print(msg, end='', flush=True)
                if f'02_continuous_reader] block_num: {block_num}' in msg:
                    stop = True
                    break

        except docker.errors.NotFound:
            print(f'Hyperion not found, retrying in 5 seg...')
            time.sleep(5)


@cli.command()
@click.argument('tx-id')
def wait_tx(tx_id):
    """Await for a transaction to be indexed.
    """
    stop = False

    while not stop:
        try:
            resp = requests.get(
                'http://127.0.0.1:7000/v2/history/check_transaction',
                params={
                    'id': tx_id
                }
            ).json()
            print(resp)

        except requests.exceptions.ConnectionError as e:
            print('connect error retrying in 3 seconds...') 

        if 'signatures' in resp:
            print('transaction found!')
            break
    
        time.sleep(3)
