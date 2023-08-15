#!/usr/bin/env python3

from copy import deepcopy

import pytest

from tevmc.config import testnet


conf = deepcopy(testnet.default_config)
conf['telosevm-translator']['worker_amount'] = 1
conf['telosevm-translator']['elastic_dump_size'] = 1024

@pytest.mark.config(**conf)
@pytest.mark.tevmc_params(wait=False)
def test_indexer_restart_multi_during_sync(tevmc_testnet):
    tevmc = tevmc_testnet

    for i in range(20):
        tevmc.cleos.wait_blocks(10 * 1000)
        tevmc.restart_translator()

        for msg in tevmc.stream_logs('telosevm-translator'):
            if 'starting from genesis' in msg:
                assert False

            elif 'found!' in msg:
                break
