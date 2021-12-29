#!/usr/bin/env python3

import time
import logging

import click
import psutil
import requests

from .cli import cli


@cli.command()
@click.argument('contract')
def is_indexed(contract):
    """Check if a contract has been indexed by hyperion.
    """
    stop = False

    while not stop:
        try:
            resp = requests.get(
                'http://127.0.0.1:7000/v2/history/get_actions',
                params={
                    'account': contract
                }
            ).json()
            logging.info(resp)

        except requests.exceptions.ConnectionError as e:
            logging.critical(e)

        if 'actions' in resp and len(resp['actions']) > 0:
            logging.info(resp)
            logging.critical("\n\n\nINDEXED\n\n\n")
            stop = True
            break

        logging.info(f'retry')
        logging.info(f'mem stats: {psutil.virtual_memory()}')
        try:
            resp = requests.get(
                'http://127.0.0.1:7000/v2/health').json()

            for service in resp['health']:
                if service['status'] == 'OK':
                    pass
                elif service['status'] == 'Warning':
                    logging.warning(service)
                else:
                    logging.critical(service)
                    stop = True

        except requests.exceptions.ConnectionError as e:
            logging.critical(e)

        time.sleep(1)
