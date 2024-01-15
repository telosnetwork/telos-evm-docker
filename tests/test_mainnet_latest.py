#!/usr/bin/env python3

import pytest

@pytest.mark.services('nodeos')
@pytest.mark.tevmc_params(from_latest=True)
def test_start_from_latest(tevmc_mainnet):
    ...
