#!/usr/bin/env python3

from setuptools import setup, find_packages


setup(
    name='tevmc',
    version='0.1a0',
    packages=find_packages(),
    install_requires=[
        'tqdm',
        'click',
        'pytest',
        'psutil',
        'docker',
        'natsort',
        'requests',
        'daemonize',
        'simple-rlp',
        'py_eosio@git+https://github.com/guilledk/py-eosio.git@docker_only'
    ],
    entry_points={
        'console_scripts': [
            'tevmc = tevmc.cmdline:cli',
        ],
    },
)
