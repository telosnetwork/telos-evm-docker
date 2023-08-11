#!/usr/bin/env python3

import pytest
import logging

from pathlib import Path

from tevmc.config import (
    local, testnet, mainnet,
)

from tevmc.testing import bootstrap_test_stack

from tevmc.testing.fixtures.local import tevm_node as tevmc_local
from tevmc.testing.fixtures.local import tevm_node_non_random as tevmc_local_non_rand
from tevmc.testing.fixtures.local import nodeos as tevmc_local_only_nodeos

from tevmc.testing.fixtures.testnet import tevm_node as tevmc_testnet
from tevmc.testing.fixtures.testnet import tevm_node_latest as tevmc_testnet_latest
from tevmc.testing.fixtures.testnet import tevm_node_no_wait as tevmc_testnet_no_wait
from tevmc.testing.fixtures.testnet import nodeos_latest as nodeos_testnet_latest

from tevmc.testing.fixtures.mainnet import tevm_node as tevmc_mainnet
from tevmc.testing.fixtures.mainnet import tevm_node_latest as tevmc_mainnet_latest
from tevmc.testing.fixtures.mainnet import tevm_node_no_wait as tevmc_mainnet_no_wait


@pytest.fixture(scope='module')
def testnet_from_228038712(tmp_path_factory):
    import zstandard as zstd
    from urllib.request import urlretrieve

    snapshots_dir = Path('tests/tevmc/snapshots')
    snapshots_dir.mkdir(exist_ok=True, parents=True)

    snapshot_name = 'snapshot-2023-04-05-14-telostest-v6-0228038712.bin'
    host_snapshot = str(snapshots_dir / snapshot_name)
    if not ((snapshots_dir / snapshot_name).is_file()):
        # finally retrieve
        logging.info('Dowloading snapshot...')
        urlretrieve(
            'https://pub.store.eosnation.io/telostest-snapshots/snapshot-2023-04-05-14-telostest-v6-0228038712.bin.zst',
            host_snapshot + '.zst'
        )

        logging.info('done, decompress...')
        dctx = zstd.ZstdDecompressor()
        with open(host_snapshot + '.zst', 'rb') as ifh:
            with open(host_snapshot, 'wb') as ofh:
                dctx.copy_stream(ifh, ofh)

    config = dict(testnet.default_config)
    config['nodeos']['snapshot'] = f'/root/{snapshot_name}'
    config['nodeos']['ini']['plugins'].append('eosio::producer_api_plugin')

    config['telosevm-translator']['start_block'] = 228039000
    config['telosevm-translator']['deploy_block'] = 228039000
    config['telosevm-translator']['prev_hash'] = '30f184986cccf4725a8dc69c81030a7515d7f84ff18a0452c6cc6978488ce58e'

    logging.info('done, starting tevmc...')

    with bootstrap_test_stack(
        tmp_path_factory,
        config,
        wait=False,
        host_snapshot=host_snapshot,
        services=['elastic', 'nodeos', 'indexer']
    ) as tevmc:
        yield tevmc
