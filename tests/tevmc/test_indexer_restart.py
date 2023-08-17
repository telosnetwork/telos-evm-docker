#!/usr/bin/env python3

import pytest


@pytest.mark.services('elastic', 'nodeos', 'indexer')
def test_indexer_restart_simple(tevmc_local):
    tevmc = tevmc_local

    tevmc.restart_translator()

    for msg in tevmc.stream_logs('telosevm-translator'):
        if 'starting from genesis' in msg:
            assert False

        elif 'found!' in msg:
            break
