#!/usr/bin/env python3

import time
import logging

import click
import docker
import requests

from .cli import cli


@cli.command()
@click.option(
    '--logpath', default='/tmp/tevmc.log',
    help='Log file path.')
def wait_init(logpath):
    with open(logpath, 'r') as logfile:
        while True:
            line = logfile.readline()
            if line:
                print(line, end='', flush=True)
                if 'control point reached' in line:
                    break
            else:
                time.sleep(1)


@cli.command()
@click.argument('block-num')
@click.option(
    '--endpoint', default='http://127.0.0.1:7000',
    help='Hyperion endpoint.')
def wait_block(
    block_num,
    endpoint
):
    """Await for block indexing.
    """
    stop = False

    while not stop:
        try:
            report = requests.get(
                f'{endpoint}/v2/health').json()

        except requests.exceptions.ConnectionError:
            print('Conection error, retry in 5 sec...')
            time.sleep(5)
            continue

        for info in report['health']:
            if info['service'] == 'Elasticsearch':
                if 'service_data' in info:
                    last_indexed = info['service_data']['last_indexed_block']
                    print(last_indexed)
                    if last_indexed >= int(block_num):
                        stop = True
                        break
                else:
                    print(info)

        time.sleep(1)


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
