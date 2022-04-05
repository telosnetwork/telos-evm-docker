#!/usr/bin/env python3

from setuptools import setup, find_packages


setup(
    name='tevmc',
    version='0.1a1',
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
        'simplejson',
        'simple_rlp@git+https://github.com/guilledk/simple-rlp.git',
        'py_eosio@git+https://github.com/guilledk/py-eosio.git@docker_only'
    ],
    entry_points={
        'console_scripts': [
            'tevmc = tevmc.cmdline:cli',
        ],
    },
)
