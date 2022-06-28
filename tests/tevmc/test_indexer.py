#!/usr/bin/env python3

import time


def test_indexer_restart(tevmc_local):
    tevmc = tevmc_local

    time.sleep(1)

    tevmc.stop()
    tevmc.is_relaunch = True
    
    tevmc.start()

    for msg in tevmc.stream_logs(
        tevmc.containers['telosevm-indexer']):
        if 'start from' in msg:
            assert False

        elif 'found!' in msg:
            break
