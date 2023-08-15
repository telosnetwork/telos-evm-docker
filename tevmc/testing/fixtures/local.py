#!/usr/bin/env python3

from copy import deepcopy

import pytest

from tevmc.config import local
from tevmc.testing import bootstrap_test_stack


@pytest.fixture()
def tevm_node(request, tmp_path_factory):
    request.applymarker(pytest.mark.config(**local.default_config))
    with bootstrap_test_stack(request, tmp_path_factory) as tevmc:
        yield tevmc


@pytest.fixture()
def tevm_node_non_random(request, tmp_path_factory):
    request.applymarker(pytest.mark.config(**local.default_config))
    request.applymarker(pytest.mark.randomize(False))
    with bootstrap_test_stack(request, tmp_path_factory) as tevmc:
        yield tevmc


@pytest.fixture()
def nodeos(request, tmp_path_factory):
    request.applymarker(pytest.mark.config(**local.default_config))
    request.applymarker(pytest.mark.services('nodeos'))
    with bootstrap_test_stack(request, tmp_path_factory) as tevmc:
        yield tevmc


@pytest.fixture()
def nodeos_vanilla(request, tmp_path_factory):
    config = deepcopy(local.default_config)

    config['nodeos']['nodeos_bin'] = 'nodeos-vanilla'
    del config['nodeos']['ini']['subst']

    request.applymarker(pytest.mark.config(**config))
    request.applymarker(pytest.mark.services('nodeos'))
    with bootstrap_test_stack(request, tmp_path_factory) as tevmc:
        yield tevmc
