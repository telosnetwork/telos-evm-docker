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
        'py_eosio@git+git://github.com/guilledk/py-eosio.git@docker_only'
    ],
    entry_points={
        'console_scripts': [
            'tevmc = tevmc.cmdline:cli',
        ],
    },
)
