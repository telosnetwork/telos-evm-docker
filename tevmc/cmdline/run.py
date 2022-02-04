#!/usr/bin/env python3

import time
import subprocess

import click

from tevmc.tevmc import TEVMCException

from .cli import cli


def stream_cmd(cmd):
    process = subprocess.Popen(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    
    for line in process.stdout:
        print(line.rstrip())

    process.wait()
    return process.returncode


@cli.command()
def run():
    ec = stream_cmd(['tevmc', 'build', '--headless'])

    if ec != 0:
        return ec

    ec = stream_cmd(['tevmc', 'up'])

    if ec != 0:
        return ec

    ec = stream_cmd(['tevmc', 'wait-init'])
    
    if ec != 0:
        return ec

    return 0
