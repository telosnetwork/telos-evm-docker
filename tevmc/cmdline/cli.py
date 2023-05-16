#!/usr/bin/env python3

import sys

import click
import docker


@click.group()
def cli():
    pass


def get_docker_client(timeout=60):
    try:
        return docker.from_env(timeout=timeout)

    except docker.errors.DockerException as err:
        msg = getattr(err, 'message', repr(err))
        print(f'Docker exception: {msg}')
        print('Is docker running? Do we have permission to access docker daemon?')
        sys.exit(1)
