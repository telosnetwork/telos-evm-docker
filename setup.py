#!/usr/bin/env python3

import os
from setuptools import setup, find_packages

def package_files(directory):
    paths = []
    for (path, _, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths

templates = package_files('tevmc/templates')

setup(
    name='tevmc',
    version='0.1a5',
    packages=find_packages(),
    package_data={'': templates},
    install_requires=[
        'rlp',
        'web3>=5.31.0',
        'tdqm',
        'asks',
        'flask',
        'click',
        'pytest',
        'psutil',
        'docker',
        'natsort',
        'requests',
        'iterators',
        'simplejson',
        'simple_rlp',
        'elasticsearch',
        'requests-unixsocket',
        'py-leap@git+https://github.com/guilledk/py-leap@v0.1a15'
    ],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'tevmc = tevmc.cmdline:cli',
        ],
    },
)
