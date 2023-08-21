#!/usr/bin/env python3

from copy import deepcopy

import pytest

from tevmc.config import testnet
from tevmc.testing.database import ElasticDriver


conf = deepcopy(testnet.default_config)
conf['telosevm-translator']['worker_amount'] = 100
conf['telosevm-translator']['elastic_dump_size'] = 1024

@pytest.mark.config(**conf)
@pytest.mark.tevmc_params(wait=False)
@pytest.mark.services('elastic', 'nodeos', 'indexer')
def test_indexer_restart_multi_during_sync(tevmc_testnet):
    tevmc = tevmc_testnet

    for i in range(20):
        tevmc.cleos.wait_blocks(10 * 1000)
        tevmc.restart_translator()

        elastic = ElasticDriver(tevmc.config)
        elastic.full_integrity_check()
