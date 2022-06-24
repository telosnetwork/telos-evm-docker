#!/usr/bin/env python3

import logging



def test_indexer(tevmc_local_non_rand):
    tevmc = tevmc_local_non_rand

    for msg in tevmc.stream_logs(
        tevmc.containers['telosevm-indexer']):
        logging.info(msg)
