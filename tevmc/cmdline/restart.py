#!/usr/bin/env python3

import os
import signal

import click

from .cli import cli


@cli.command()
@click.option(
    '--pid', default='tevmc.pid',
    help='Path to lock file for daemon')
def restart(pid):
    """Bring tevmc daemon down.
    """
    try:
        with open(pid, 'r') as pidfile:
            pid = int(pidfile.read())

        os.kill(pid, signal.SIGUSR1)

    except FileNotFoundError:
        print(f'Couldn\'t open pid file at {pid}')

