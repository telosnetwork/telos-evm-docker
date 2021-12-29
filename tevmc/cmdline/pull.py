#!/usr/bin/env python3

import sys
import json


import click
import docker

from tqdm import tqdm


from .cli import cli


@cli.command()
@click.option(
    '--redis-tag', default='redis:5.0.9-buster',
    help='Redis container image tag.')
@click.option(
    '--rabbitmq-tag', default='rabbitmq:3.8.3-management',
    help='Rabbitmq container image tag.')
@click.option(
    '--elasticsearch-tag', default='docker.elastic.co/elasticsearch/elasticsearch:7.13.2',
    help='Elastic search container image tag.')
@click.option(
    '--kibana-tag', default='docker.elastic.co/kibana/kibana:7.7.1',
    help='Kibana container image tag.')
def pull(**kwargs):
    """Pull required service container images.
    """
    client = docker.from_env()

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

    max_size = 54

    class DownloadInProgress:

        def __init__(self, pos: int):
            self.pos = pos
            self.prev_progress = 0
            self.prev_total = 0
            self.current_progress = 0
            self.current_total = 0
            self.bar = tqdm(pos, bar_format='{l_bar}{bar}')

        def update(self, update):
            if 'status' in update:
                status_txt = format(update['status'][:max_size], f' <{max_size}')
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


    for repo, tag in manifest:
        print(f'pulling {repo}:{tag}... ')

        bars = {}
        for chunk in client.api.pull(repo, tag=tag, stream=True):
            update = chunk.decode('utf-8')
            update = json.loads(update.rstrip())

            status = update['status']
        
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
