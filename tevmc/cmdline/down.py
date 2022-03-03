#!/usr/bin/env python3

import psutil
import click

from .cli import cli


@cli.command()
@click.option(
    '--pid', default='tevmc.pid',
    help='Path to lock file for daemon')
def down(pid):
    """Bring tevmc daemon down.
    """
    try:
        with open(pid, 'r') as pidfile:
            pid = int(pidfile.read())

        tevmcd = psutil.Process(pid)
        tevmcd.terminate()
        tevmcd.wait()

    except FileNotFoundError:
        print(f'Couldn\'t open pid file at {pid}')

