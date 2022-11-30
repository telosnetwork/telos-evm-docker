#!/usr/bin/env python3

import os
from setuptools import setup, find_packages

def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths

templates = package_files('tevmc/templates')

setup(
    name='tevmc',
    version='0.1a3',
    packages=find_packages(),
    package_data={'': templates},
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
        'py_eosio@git+https://github.com/guilledk/py-eosio.git@host_deploy'
    ],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'tevmc = tevmc.cmdline:cli',
        ],
    },
)
