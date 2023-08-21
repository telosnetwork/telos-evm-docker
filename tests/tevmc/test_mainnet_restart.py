#!/usr/bin/env python3

import pytest

from tevmc.testing.database import ElasticDriver


@pytest.mark.tevmc_params(wait=False)
def test_restart(tevmc_mainnet):
    tevmc = tevmc_mainnet

    tevmc.stop()

    assert (tevmc.docker_wd /
        'leap/data/blocks/blocks.log').is_file()

    tevmc.start()

    ElasticDriver(tevmc_mainnet.config).full_integrity_check()
