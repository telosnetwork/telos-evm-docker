#!/usr/bin/env python3

import sys
import json

import click
import docker

from tqdm import tqdm

from .cli import cli, get_docker_client
from ..config import * 


class DownloadInProgress:
    """ Helper class to manage download progress bar
    """

    def __init__(self, pos: int):
        self.pos = pos
        self.prev_progress = 0
        self.prev_total = 0
        self.current_progress = 0
        self.current_total = 0
        self.bar = tqdm(pos, bar_format='{l_bar}{bar}')

    def update(self, update):
        if 'status' in update:
            status_txt = format(
                update['status'][:MAX_STATUS_SIZE], f' <{MAX_STATUS_SIZE}')
            self.bar.set_description(desc=status_txt)

        if 'progressDetail' in update:
            detail = update['progressDetail']

            if 'current' not in detail or 'total' not in detail:
                return

            progress = detail['current']
            total = detail['total']
            
            if total != self.current_total:
                self.prev_total = self.current_total
                self.bar.reset(total=total)
                self.current_total = total

            if progress != self.current_progress:
                self.prev_progress = self.current_progress
                self.bar.update(n=progress)
                self.curent_progress = progress

    def close(self):
        self.bar.close()

@cli.command()
@click.option(
    '--headless/--interactive', default=False,
    help='Display pretty output or just stream logs.')
@click.option(
    '--redis-tag', default=REDIS_TAG,
    help='Redis container image tag.')
@click.option(
    '--rabbitmq-tag', default=RABBITMQ_TAG,
    help='Rabbitmq container image tag.')
@click.option(
    '--elasticsearch-tag', default=ELASTICSEARCH_TAG,
    help='Elastic search container image tag.')
@click.option(
    '--kibana-tag', default=KIBANA_TAG,
    help='Kibana container image tag.')
def pull(headless, **kwargs):
    """Pull required service container images.
    """
    client = get_docker_client()

    manifest = []
    for key, arg in kwargs.items():
        try:
            repo, tag = arg.split(':')

        except ValueError:
            print(
                f'Malformed tag {key}=\'{arg}\','
                f' must be of format \'{repo}:{tag}\'.')
            sys.exit(1)
    
        manifest.append((repo, tag))

    for repo, tag in manifest:
        print(f'pulling {repo}:{tag}... ')

        bars = {}
        for chunk in client.api.pull(repo, tag=tag, stream=True):
            update = chunk.decode('utf-8')
            update = json.loads(update.rstrip())

            _id = update.get('id', None)
            status = update.get('status', None)
            detail = update.get('progressDetail', None)

            if headless:
                print(f'{_id}: {status} {detail}')
                continue
        
            if ('Pulling from library' in status or
                'id' not in update):
                continue

            _id = update['id']

            if status == 'Pulling fs layer':
                bars[_id] = DownloadInProgress(len(bars))

            if _id in bars:
                bars[_id].update(update)

        for bar_id, bar in bars.items():
            bar.close()
