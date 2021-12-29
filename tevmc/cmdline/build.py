#!/usr/bin/env python3

import sys
import json


import click
import docker

from tqdm import tqdm


from .cli import cli


@cli.command()
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

    max_size = 54 

    for build_args in builds:
        stream = ''
        msg = f'building {build_args["tag"]}'
        desc = format(f'{msg[:max_size]}', f' <{max_size}')
        bar = tqdm(
            desc=desc,
            bar_format='{l_bar}{bar}'
        )
        for chunk in client.api.build(**build_args):
            update = None
            _str = chunk.decode('utf-8').rstrip()

            # sometimes several json packets are sent per chunk
            splt_str = _str.split('\n')
            
            for packet in splt_str:
                msg = json.loads(packet)
                update = msg.get('status', None)
                update = msg.get('stream', None)

                if update:
                    stream += update
                    if update.startswith('Step'):
                        """Docker sends build updates with format
                            'Step current/total'
                        Use it to update the progress bar.
                        """
                        step_info = update.split(' ')[1]
                        step_info = step_info.split('/')
                        current = int(step_info[0])
                        total = int(step_info[1])

                        update = update.rstrip()

                        bar.reset(total=total)
                        bar.update(current)

                        bar.set_description(
                            desc=format(f'{update[:max_size]}', f' <{max_size}'))

        final_msg = f'built {build_args["tag"]}'
        bar.set_description(
            desc=format(f'{final_msg[:max_size]}', f' <{max_size}'))
        bar.close()

        try:
            client.images.get(build_args['tag'])

        except docker.errors.NotFound:
            print(
                f'couldn\'t build container {build_args["tag"]} at '
                f'{build_args["path"]}')
            print('build log:')
            print(stream)
            sys.exit(1)
