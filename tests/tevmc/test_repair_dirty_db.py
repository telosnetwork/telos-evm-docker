#!/usr/bin/env python3

import logging

import pytest

from tevmc.cmdline.repair import perform_data_repair
from tevmc.config import load_config


@pytest.mark.randomize(False)
@pytest.mark.tevmc_params(is_producer=False)
@pytest.mark.services('redis', 'elastic', 'nodeos', 'indexer')
def test_repair_dirty_db(tevmc_mainnet):
    tevmc = tevmc_mainnet

    tevmc.cleos.wait_blocks(100_000)

    # ungracefull nodeos stop
    tevmc.containers['nodeos'].stop()

    # assert db is dirty
    tevmc.is_nodeos_relaunch = True
    tevmc.start_nodeos(do_init=False)
    is_dirty = False
    for line in tevmc.stream_logs('nodeos'):
        logging.info(line)
        is_dirty = 'database dirty flag set (likely due to unclean shutdown)' in line
        if is_dirty:
            break

    assert is_dirty

    # tear down node
    tevmc.stop()

    # run repair
    perform_data_repair(
        tevmc.root_pwd / 'tevmc.json', progress=False)

    # update config
    tevmc.is_nodeos_relaunch = False
    tevmc.config = load_config(tevmc.root_pwd, 'tevmc.json')

    # pull up node
    tevmc.start()

    breakpoint()
