#!/usr/bin/env python3

import sys
import json

import click
import docker

from tqdm import tqdm

from .cli import cli
from ..config import MAX_STATUS_SIZE


class BuildInProgress:
    """ Helper class to manage build progress bar
    """

    def __init__(self):
        self.prev_progress = 0
        self.prev_total = 0
        self.current_progress = 0
        self.current_total = 0
        self.status = ''
        self.bar = tqdm(bar_format='{l_bar}{bar}')

    def set_status(self, status: str):
        new_status = format(
            f'{status[:MAX_STATUS_SIZE]}', f' <{MAX_STATUS_SIZE}')

        if new_status != self.status:
            self.status = new_status
            self.bar.set_description(desc=new_status)

    def update(self, update):
        if update.startswith('Step'):
            """Docker sends build updates with format
                'Step progress/total'
            Use it to update the progress bar.
            """
            step_info = update.split(' ')[1]
            step_info = step_info.split('/')
            progress = int(step_info[0])
            total = int(step_info[1])

            update = update.rstrip()
            
            if total != self.current_total:
                self.prev_total = self.current_total
                self.bar.reset(total=total)
                self.current_total = total

            if progress != self.current_progress:
                self.prev_progress = self.current_progress
                self.bar.update(n=progress)
                self.curent_progress = progress

            self.set_status(update) 

    def close(self):
        self.bar.close()

@cli.command()
@click.option(
    '--headless/--interactive', default=False,
    help='Display pretty output or just stream logs.')
@click.option(
    '--eosio-path', default='docker/eosio',
    help='Path to eosio docker directory')
@click.option(
    '--eosio-tag', default='eosio:2.1.0-evm',
    help='Eosio container tag')
@click.option(
    '--hyperion-path', default='docker/hyperion',
    help='Path to hyperion docker directory')
@click.option(
    '--hyperion-tag', default='telos.net/hyperion:0.1.0',
    help='Eosio container tag')
def build(
    headless,
    eosio_path,
    eosio_tag,
    hyperion_path,
    hyperion_tag
):
    """Build in-repo docker containers.
    """
    client = docker.from_env()

    builds = [
        {'path': eosio_path, 'tag': eosio_tag},
        {'path': hyperion_path, 'tag': hyperion_tag}
    ]

    for build_args in builds:
        if not headless:
            stream = ''
            msg = f'building {build_args["tag"]}'
            bar = BuildInProgress()
            bar.set_status(msg)

        for chunk in client.api.build(**build_args):
            update = None
            _str = chunk.decode('utf-8').rstrip()

            # sometimes several json packets are sent per chunk
            splt_str = _str.split('\n')
            
            for packet in splt_str:
                msg = json.loads(packet)
                status = msg.get('status', None)
                status = msg.get('stream', None)

                if status:
                    if headless:
                        print(status, end='')
                    else:
                        stream += status
                        bar.update(status)
    
        if not headless:
            bar.set_status(f'built {build_args["tag"]}')
            bar.close()

        try:
            client.images.get(build_args['tag'])

        except docker.errors.NotFound:
            print(
                f'couldn\'t build container {build_args["tag"]} at '
                f'{build_args["path"]}')
            if not headless:
                print('build log:')
                print(stream)
            sys.exit(1)
