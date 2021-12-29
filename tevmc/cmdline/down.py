#!/usr/bin/env python3

import os
import signal

import click

from .cli import cli


@cli.command()
@click.option(
    '--pid', default='/tmp/tevmc.pid',
    help='Path to lock file for daemon')
def down(pid):
    """Bring tevmc daemon down.
    """
    try:
        with open(pid, 'r') as pidfile:
            pid = pidfile.read()

        os.kill(int(pid), signal.SIGINT)

    except FileNotFoundError:
        print(f'Couldn\'t open pid file at {pid}')

