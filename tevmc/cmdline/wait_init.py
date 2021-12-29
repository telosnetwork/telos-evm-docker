#!/usr/bin/env python3

import click

from .cli import cli


@cli.command()
@click.option(
    '--show/--no-show', default=False,
    help='Show output while waiting for bootstrap.')
@click.option(
    '--logpath', default='/tmp/tevmc.log',
    help='Log file path.')
def wait_init(show, logpath):
    """Await for full daemon initialization.
    """

    with open(logpath, 'r') as logfile:
        line = ''
        try:
            while 'control point reached' not in line:
                line = logfile.readline()
                if show:
                    print(line, end='', flush=True)

        except KeyboardInterrupt:
            print('Interrupted.')
