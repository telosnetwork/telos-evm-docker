#!/usr/bin/env python3

import pytest


@pytest.mark.tevmc_params(wait=False)
def test_restart(tevmc_testnet):
    tevmc = tevmc_testnet

    tevmc.stop()

    assert (tevmc.docker_wd /
        'leap/data/blocks/blocks.log').is_file()

    tevmc.start()

