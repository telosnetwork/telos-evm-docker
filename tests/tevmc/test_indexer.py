#!/usr/bin/env python3

import time
import logging



# def test_indexer(tevmc_local_non_rand):
#     tevmc = tevmc_local_non_rand
# 
#     for msg in tevmc.stream_logs(
#         tevmc.containers['telosevm-indexer']):
#         logging.info(msg)


def test_indexer_restart(tevmc_local):
    tevmc = tevmc_local

    time.sleep(1)

    tevmc.stop()
    tevmc.is_relaunch = True
    
    tevmc.start()

    for msg in tevmc.stream_logs(
        tevmc.containers['telosevm-indexer']):
        if 'not found' in msg:
            assert False

        elif 'found!' in msg:
            break

