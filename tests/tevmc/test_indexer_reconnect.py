#!/usr/bin/env python3

import time

import pytest

from tevmc.testing.database import ElasticDriver


@pytest.mark.services('elastic', 'nodeos', 'indexer')
def test_indexer_reconnect(tevmc_local):
    tevmc = tevmc_local

    for msg in tevmc.stream_logs('telosevm-translator'):
        if 'drained' in msg:
            break

    tevmc.cleos.stop_nodeos(
        from_file=tevmc.config['nodeos']['log_path'])
    tevmc.is_nodeos_relaunch = True

    time.sleep(4)

    tevmc.start_nodeos()

    for msg in tevmc.stream_logs('telosevm-translator', from_latest=True):
        tevmc.logger.info(msg)
        if 'drained' in msg:
            break

    elastic = ElasticDriver(tevmc.config)
    elastic.full_integrity_check()
