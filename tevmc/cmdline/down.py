#!/usr/bin/env python3

import signal
import psutil

from pathlib import Path

import click

from .cli import cli


@cli.command()
@click.option(
    '--pid', default='tevmc.pid',
    help='Path to lock file for daemon')
def down(pid):
    """Bring tevmc daemon down.
    """
    pid_path = pid
    try:
        with open(pid, 'r') as pidfile:
            pid = int(pidfile.read())

        tevmcd = psutil.Process(pid)
        tevmcd.send_signal(signal.SIGINT)
        tevmcd.wait()

        Path(pid_path).unlink(missing_ok=True)

    except FileNotFoundError:
        print(f'Couldn\'t open pid file at {pid}')

